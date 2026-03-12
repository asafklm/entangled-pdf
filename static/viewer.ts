/**
 * PdfServer Viewer JavaScript
 *
 * Handles PDF rendering, WebSocket communication, and SyncTeX synchronization.
 * Refactored version using modular architecture.
 * 
 * TODO: Known Issues
 * 1. App switching scroll: Switching back and forth between browser and other apps causes 
 *    the PDF to scroll to the top. Desired behavior: leave PDF view unchanged unless 
 *    user performed forward sync. This appears to be a Safari/iOS browser behavior that 
 *    is difficult to prevent.
 * 
 * 2. Red dot position: Fixed - marker now appears on the left margin.
 * 
 * 3. Sync back lag: The inverse search confirmation button is lagging or unresponsive. 
 *    This needs investigation into the tooltip event handling and WebSocket message 
 *    sending timing.
 */

import { PDFRenderer, initPDFJSWorker, createPDFUrl } from './pdf-renderer.js';
import { WebSocketManager, type MessageHandler } from './websocket-manager.js';
import { KeyboardHandler } from './keyboard-handler.js';
import { StateManager, createStateManager } from './state-manager.js';
import { NotificationManager, createErrorBanner } from './notification-manager.js';
import { 
  scrollToPageWithRetry, 
  scrollBy, 
  scrollHorizontallyBy,
  scrollFullPage,
  navigateToNextPage,
  navigateToPreviousPage,
  navigateToPage,
  getUpperViewportY,
  type ScrollPosition,
} from './scroll-manager.js';
import { 
  showMarkerAtPdfCoordinates,
  showMarkerAtPage,
  clearAllMarkers,
} from './marker-manager.js';
import { pdfYToPixels } from './coordinate-utils.js';
import {
  createInverseSearchTooltip,
  hideActiveTooltip,
  isClickOutsideTooltip,
  showSyncError,
} from './tooltip-manager.js';
import { LongPressDetector } from './long-press-handler.js';
import type { PdfPosition, ViewportPosition, StateUpdate, WebSocketMessage } from './types.js';
import { MARKER_DELAY_AFTER_RELOAD } from './constants.js';
import { clientLogger } from './client-logger.js';

// Configuration from server
const CONFIG = window.PDF_CONFIG || { 
  port: 8431, 
  filename: 'document.pdf', 
  mtime: 0, 
  token: null, 
  inverse_search_enabled: false 
};

// DOM Elements
const container = document.getElementById('viewer-container');
const errorBanner = createErrorBanner(document.getElementById('error-banner'));
const noPdfMessage = document.getElementById('no-pdf-message');
const connectionStatus = document.getElementById('connection-status');

if (!container) {
  throw new Error('Viewer container not found');
}

// Use non-null assertion for container throughout
type NonNullContainer = HTMLElement;
const viewerContainer: NonNullContainer = container;

// Initialize PDF.js worker
initPDFJSWorker('/pdfjs/pdf.worker.mjs');

// Create managers
const pdfRenderer = new PDFRenderer(viewerContainer);
const stateManager = createStateManager(CONFIG);
const notificationManager = new NotificationManager();
const wsManager = new WebSocketManager(window.location.hostname, CONFIG.port, CONFIG.token);

// Track PDF loading state to prevent concurrent reloads
let isLoadingPDF = false;

// Attach logger to WebSocket
clientLogger.attachWebSocket(wsManager);

// Setup WebSocket message handlers
wsManager.on('synctex', handleSyncTeXMessage as MessageHandler);
wsManager.on('reload', handleReloadMessage as MessageHandler);

// Connection status indicator functions
function updateConnectionStatus(connected: boolean): void {
  if (!connectionStatus || !CONFIG.inverse_search_enabled) return;
  
  if (connected) {
    connectionStatus.className = 'connected';
    connectionStatus.querySelector('.status-text')!.textContent = 'Connected';
    connectionStatus.style.display = 'flex';
  } else {
    connectionStatus.className = 'disconnected';
    connectionStatus.querySelector('.status-text')!.textContent = 'Reconnect';
    connectionStatus.style.display = 'flex';
  }
}

function hideConnectionStatus(): void {
  if (connectionStatus) {
    connectionStatus.style.display = 'none';
  }
}

// Setup connection status click handler
if (connectionStatus) {
  connectionStatus.addEventListener('click', () => {
    if (connectionStatus.classList.contains('disconnected')) {
      // Navigate to auth page to get new token
      window.location.href = '/view';
    }
  });
}

// Setup WebSocket connection callbacks
wsManager.onError(() => {
  // Silent error - connection status indicator shows state
  updateConnectionStatus(false);
});

wsManager.onConnect(() => {
  updateConnectionStatus(true);
});

wsManager.onDisconnect((code) => {
  // Show disconnected state on indicator
  updateConnectionStatus(false);
  // Note: No intrusive banner - user can still view PDF
});

wsManager.onInvalidToken(() => {
  // Server restarted with new token - show disconnected state
  updateConnectionStatus(false);
  // Note: User can still view PDF and use forward sync
  // They just can't do inverse search until they re-authenticate
});

// Show initial connection status only if inverse search is enabled
if (CONFIG.inverse_search_enabled) {
  updateConnectionStatus(false);
}

// Connect to WebSocket
wsManager.connect();

// Create keyboard handler
const keyboardHandler = new KeyboardHandler({
  onScrollDown: () => scrollBy(viewerContainer, 40),
  onScrollUp: () => scrollBy(viewerContainer, -40),
  onScrollLeft: () => scrollHorizontallyBy(viewerContainer, -40),
  onScrollRight: () => scrollHorizontallyBy(viewerContainer, 40),
  onNextPage: () => {
    const currentPage = stateManager.currentPage;
    const doc = pdfRenderer.document;
    if (currentPage && doc) {
      navigateToNextPage(viewerContainer, pdfRenderer.getPageElements(), currentPage, doc.numPages);
    }
  },
  onPreviousPage: () => {
    const currentPage = stateManager.currentPage;
    if (currentPage) {
      navigateToPreviousPage(viewerContainer, pdfRenderer.getPageElements(), currentPage);
    }
  },
  onFirstPage: () => {
    navigateToPage(viewerContainer, pdfRenderer.getPageElements(), 1);
    stateManager.updatePosition(1);
  },
  onLastPage: () => {
    const doc = pdfRenderer.document;
    if (doc) {
      navigateToPage(viewerContainer, pdfRenderer.getPageElements(), doc.numPages);
      stateManager.updatePosition(doc.numPages);
    }
  },
  onScrollPageDown: (shiftKey) => {
    scrollFullPage(viewerContainer, shiftKey ? 'up' : 'down');
  },
  onInverseSearch: performKeyboardInverseSearch,
});

keyboardHandler.attach();

// Long press detector for inverse search
const longPressDetector = new LongPressDetector({
  duration: 500,
  moveThreshold: 10,
  onLongPress: handleLongPress,
  isInteractiveElement: (target) => {
    if (!target) return false;
    const element = target as HTMLElement;
    return element.tagName === 'A' || 
           element.tagName === 'BUTTON' || 
           element.isContentEditable;
  },
});

// Mouse event handlers for long press
const mouseHandlers = longPressDetector.createMouseHandlers(getPdfPositionAtPoint);
viewerContainer.addEventListener('mousedown', mouseHandlers.onMouseDown);
viewerContainer.addEventListener('mousemove', mouseHandlers.onMouseMove);
viewerContainer.addEventListener('mouseup', mouseHandlers.onMouseUp);
viewerContainer.addEventListener('mouseleave', mouseHandlers.onMouseLeave);

// Touch event handlers for long press
const touchHandlers = longPressDetector.createTouchHandlers(getPdfPositionAtPoint);
viewerContainer.addEventListener('touchstart', touchHandlers.onTouchStart, { passive: true });
viewerContainer.addEventListener('touchmove', touchHandlers.onTouchMove, { passive: true });
viewerContainer.addEventListener('touchend', touchHandlers.onTouchEnd);
viewerContainer.addEventListener('touchcancel', touchHandlers.onTouchCancel);

// Click handler for focus and tooltip dismissal
document.addEventListener('click', (event: MouseEvent) => {
  // Focus container when clicking anywhere
  if (document.activeElement !== viewerContainer) {
    viewerContainer.focus();
  }
  
  // Hide tooltip if clicking outside
  if (isClickOutsideTooltip(event.clientX, event.clientY)) {
    hideActiveTooltip();
  }
});

// Simple visibility change handler - just reconnects WebSocket
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    viewerContainer.focus();
    syncState();
    
    // Reconnect WebSocket if needed
    setTimeout(() => {
      if (!wsManager.isConnected) {
        wsManager.connect();
      }
    }, 100);
  }
});

// Pageshow event for Android back-forward cache
window.addEventListener('pageshow', (event: PageTransitionEvent) => {
  if (event.persisted) {
    syncState();
    
    setTimeout(() => {
      if (!wsManager.isConnected) {
        wsManager.connect();
      }
    }, 100);
  }
});

/**
 * Handle SyncTeX message from WebSocket
 */
function handleSyncTeXMessage(data: WebSocketMessage): void {
  if (!data.page) return;
  applyStateUpdate({
    page: data.page,
    x: data.x,
    y: data.y,
    last_sync_time: data.last_sync_time,
    action: data.action,
  }, MARKER_DELAY_AFTER_RELOAD, 0, true);
}

/**
 * Apply state update and scroll to position
 */
function applyStateUpdate(data: StateUpdate, delay = 0, attempt = 0, isForwardSync = false): void {
  stateManager.applyUpdate(data);
  
  const pageNum = data.page;
  const x = data.x;
  const y = data.y;
  
  if (y != null) {
    const canvas = pdfRenderer.getCanvas(pageNum);
    const scale = pdfRenderer.getPageScale(pageNum);
    
    if (canvas) {
      // Convert PDF points to pixels using proper coordinate conversion
      const pixelY = pdfYToPixels(canvas, y, scale);
      
      const pageElements = pdfRenderer.getPageElements();
      scrollToPageWithRetry(viewerContainer, pageElements, pageNum, pixelY, 0, 'auto', (from: ScrollPosition, to: ScrollPosition) => {
        clientLogger.logScroll(from, to);
      });
      
      setTimeout(() => {
        // Show marker at Y position only - red dot should appear on left margin
        // Don't pass x coordinate to keep marker on left margin (not at text position)
        showMarkerAtPage(
          pdfRenderer.getPageElements(),
          pdfRenderer.getPageScales(),
          pageNum,
          y
          // x is intentionally omitted - marker stays on left margin per CSS default
        );
      }, delay);
    } else if (attempt < 10) {
      // Canvas not ready yet - retry after a short delay
      setTimeout(() => {
        applyStateUpdate(data, delay, attempt + 1, isForwardSync);
      }, 100);
    }
  } else if (isForwardSync) {
    // Only scroll to page without position if this is a forward sync
    scrollToPageWithRetry(viewerContainer, pdfRenderer.getPageElements(), pageNum, undefined, 0, 'auto', (from: ScrollPosition, to: ScrollPosition) => {
      clientLogger.logScroll(from, to);
    });
  }
}

/**
 * Handle reload message from WebSocket
 */
function handleReloadMessage(data: WebSocketMessage): void {
  const reloadMtime = data.pdf_mtime;
  if (reloadMtime && reloadMtime > 0) {
    CONFIG.mtime = reloadMtime;
    // Update state manager immediately to prevent race condition with syncState
    // This ensures syncState() won't trigger another reload for the same mtime
    stateManager.updatePdfMtime(reloadMtime);
  }
  reloadPDF();
}

/**
 * Reload the PDF document
 */
async function reloadPDF(): Promise<void> {
  // Prevent concurrent reloads - Safari iPad fires multiple events that can trigger reload
  if (isLoadingPDF) {
    console.log("[reloadPDF] PDF reload already in progress, skipping duplicate request");
    return;
  }
  
  isLoadingPDF = true;
  
  try {
    // Hide no-pdf message and show container
    if (noPdfMessage) {
      noPdfMessage.style.display = 'none';
    }
    viewerContainer.style.display = 'block';
    
    // Clear existing state
    pdfRenderer.clear();
    stateManager.reset();
    clearAllMarkers();
    
    const url = createPDFUrl('/get-pdf', CONFIG.mtime);
    await pdfRenderer.load(url);
    
    // Log PDF load
    clientLogger.logPdfLoad(CONFIG.filename, CONFIG.mtime);
    
    // Apply pending state update if exists (from syncState during reload)
    const pending = stateManager.pendingUpdate;
    if (pending) {
      applyStateUpdate(pending, MARKER_DELAY_AFTER_RELOAD);
      stateManager.setPendingUpdate(null);
    }
    // Don't scroll to page 1 - let user stay where they are
  } catch (error) {
    console.error('Failed to reload PDF:', error);
    stateManager.setPendingUpdate(null);
    notificationManager.error('Failed to reload PDF. Please check that the file exists.');
  } finally {
    isLoadingPDF = false;
  }
}

/**
 * Synchronize state when tab regains focus or reconnects.
 * 
 * Tracks two separate timestamps:
 * - pdf_mtime: when the PDF file was last modified (requires reload)
 * - last_sync_time: when last forward sync occurred (requires scroll)
 */
async function syncState(): Promise<void> {
  try {
    const res = await fetch('/state');
    const data: StateUpdate = await res.json();
    
    // Check if PDF file has changed
    const pdfChanged = stateManager.isPdfChanged(data);
    
    // Check if there's a newer forward sync (scroll) to apply
    const newSync = stateManager.isNewerSync(data);
    
    // Update file tracking info if changed
    if (data.pdf_file && data.pdf_file !== CONFIG.filename) {
      CONFIG.filename = data.pdf_file;
    }
    
    if (pdfChanged && data.pdf_mtime) {
      CONFIG.mtime = data.pdf_mtime;
    }
    
    if (pdfChanged) {
      // PDF has changed - need to reload
      if (isLoadingPDF) {
        // PDF is already loading, just store pending scroll for when it completes
        if (newSync) {
          stateManager.setPendingUpdate(data);
        }
        // Still update timestamps so we don't check again
      } else {
        // Not currently loading, proceed with reload
        if (newSync) {
          // Both PDF changed AND new sync exists: store scroll info for after reload
          stateManager.setPendingUpdate(data);
        }
        stateManager.setPdfLoaded(true);
        await reloadPDF();
      }
    } else if (newSync) {
      // Only scroll changed, PDF is same: just scroll to new position
      stateManager.setPdfLoaded(true);
      applyStateUpdate(data, 0, 0, true);
    }
    
    // Update our tracked timestamps
    if (data.pdf_mtime) {
      stateManager.updatePdfMtime(data.pdf_mtime);
    }
    if (data.last_sync_time) {
      stateManager.updateSyncTime(data);
    }
  } catch (e) {
    console.error('Sync error', e);
  }
}

/**
 * Get PDF position at a viewport point
 */
function getPdfPositionAtPoint(position: ViewportPosition): PdfPosition | null {
  const clientX = position.clientX;
  const clientY = position.clientY;
  
  // Find which page contains this point
  const pageNum = pdfRenderer.findPageAtY(clientY);
  if (!pageNum) return null;
  
  const page = pdfRenderer.renderedPages.get(pageNum);
  if (!page) return null;
  
  const wrapperRect = page.wrapper.getBoundingClientRect();
  const relativeX = clientX - wrapperRect.left;
  const relativeY = clientY - wrapperRect.top;
  
  const pdfScale = page.scale;
  const x = relativeX / pdfScale;
  const y = relativeY / pdfScale;
  
  return { page: pageNum, x, y };
}

/**
 * Handle long press activation
 */
function handleLongPress(position: ViewportPosition, pdfPosition: PdfPosition): void {
  if (!CONFIG.inverse_search_enabled) return;
  
  createInverseSearchTooltip(
    position,
    pdfPosition,
    () => {
      if (wsManager.isConnected) {
        performInverseSearch(pdfPosition);
      } else {
        // Navigate to auth page when not connected
        window.location.href = '/view';
      }
    },
    () => hideActiveTooltip(),
    wsManager.isConnected
  );
}

/**
 * Perform inverse search at PDF position
 */
async function performInverseSearch(position: PdfPosition): Promise<void> {
  const success = await wsManager.sendInverseSearch(position.page, position.x, position.y);
  
  if (success) {
    // Show red dot as feedback
    showMarkerAtPage(
      pdfRenderer.getPageElements(),
      pdfRenderer.getPageScales(),
      position.page,
      position.y,
      position.x
    );
  } else {
    showSyncError('⚠️ Sync Failed — Connection lost. Refresh page or wait for auto-reconnect.');
  }
}

/**
 * Perform inverse search at upper viewport position (keyboard shortcut)
 */
async function performKeyboardInverseSearch(): Promise<void> {
  if (!CONFIG.inverse_search_enabled) {
    console.warn('Inverse search not enabled');
    return;
  }
  
  const containerRect = viewerContainer.getBoundingClientRect();
  const viewportY = getUpperViewportY(viewerContainer);
  const clientX = containerRect.left + (containerRect.width / 2);
  const clientY = containerRect.top + viewportY;
  
  const position: ViewportPosition = { clientX, clientY };
  const pdfPosition = getPdfPositionAtPoint(position);
  
  if (!pdfPosition) {
    console.warn('Could not calculate PDF coordinates');
    return;
  }
  
  createInverseSearchTooltip(
    position,
    pdfPosition,
    () => {
      if (wsManager.isConnected) {
        performInverseSearch(pdfPosition);
      } else {
        // Navigate to auth page when not connected
        window.location.href = '/view';
      }
    },
    () => hideActiveTooltip(),
    wsManager.isConnected
  );
}

// Initialize
if (CONFIG.filename === 'no-pdf-loaded') {
  console.log('No PDF loaded yet');
  if (noPdfMessage) {
    noPdfMessage.style.display = 'block';
  }
  viewerContainer.style.display = 'none';
} else {
  stateManager.setPdfLoaded(true);
  
  const url = createPDFUrl('/get-pdf', CONFIG.mtime);
  pdfRenderer.load(url)
    .then(() => {
      // Log initial PDF load
      clientLogger.logPdfLoad(CONFIG.filename, CONFIG.mtime);
      
      // Note: syncState() not needed here - initial load already has the correct PDF
      // syncState() is only called on visibilitychange/pageshow for reconnection scenarios
      viewerContainer.focus();
    })
    .catch((error: Error) => {
      console.error('Failed to load PDF:', error);
      notificationManager.error('Failed to load PDF. Please check that the file exists.');
    });
}
