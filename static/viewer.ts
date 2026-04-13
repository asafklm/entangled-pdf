/**
 * EntangledPdf Viewer JavaScript
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
import type { PdfPosition, ViewportPosition, StateUpdate, WebSocketMessage } from './types.js';
import { MARKER_DELAY_AFTER_RELOAD } from './constants.js';
import { clientLogger } from './client-logger.js';
import {
  renderStatusIndicator,
  renderDetailsPanel,
  getStatusClass,
  determineStatus,
  type ConnectionStatusState,
} from './connection-status-ui.js';
import { createInputHandler } from './input-handler.js';
import { createSyncTeXController } from './synctex-controller.js';
import { createPdfLifecycle, type PdfLifecycleManager } from './pdf-lifecycle.js';

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
const connectionDetails = document.getElementById('connection-details');

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

// Create lifecycle manager (must be before syncTeXController for onPdfReload reference)
const lifecycle: PdfLifecycleManager = createPdfLifecycle({
  config: CONFIG,
  stateManager,
  pdfRenderer,
  notificationManager,
  noPdfMessage,
  viewerContainer,
  onStatusUpdate: (status) => updateConnectionStatus(wsManager.isConnected),
  onApplyStateUpdate: (data, delay) => {
    syncTeXController.applyStateUpdate(data, delay, 0, true);
  },
  onClearMarkers: clearAllMarkers,
});

// Track whether connection details panel is visible
let detailsPanelVisible = false;

// Attach logger to WebSocket
clientLogger.attachWebSocket(wsManager);

// Create SyncTeX controller
const syncTeXController = createSyncTeXController({
  config: CONFIG,
  stateManager,
  pdfRenderer,
  notificationManager,
  onPdfReload: lifecycle.reloadPDF,
  onStatusUpdate: (status) => updateConnectionStatus(wsManager.isConnected),
  onApplyStateUpdate: (data, delay, attempt, isForwardSync) => {
    const pageNum = data.page;
    const y = data.y;
    
    if (y != null) {
      const canvas = pdfRenderer.getCanvas(pageNum);
      const scale = pdfRenderer.getPageScale(pageNum);
      
      if (canvas) {
        const pixelY = pdfYToPixels(canvas, y, scale);
        const pageElements = pdfRenderer.getPageElements();
        scrollToPageWithRetry(viewerContainer, pageElements, pageNum, pixelY, 0, 'auto', (from: ScrollPosition, to: ScrollPosition) => {
          clientLogger.logScroll(from, to);
        });
        
        setTimeout(() => {
          showMarkerAtPage(
            pdfRenderer.getPageElements(),
            pdfRenderer.getPageScales(),
            pageNum,
            y
          );
        }, delay);
      } else if (attempt < 10) {
        setTimeout(() => {
          syncTeXController.applyStateUpdate(data, delay, attempt + 1, isForwardSync);
        }, 100);
      }
    } else if (isForwardSync) {
      scrollToPageWithRetry(viewerContainer, pdfRenderer.getPageElements(), pageNum, undefined, 0, 'auto', (from: ScrollPosition, to: ScrollPosition) => {
        clientLogger.logScroll(from, to);
      });
    }
  },
});

// Setup WebSocket message handlers
wsManager.on('synctex', syncTeXController.handleSyncTeXMessage as MessageHandler);
wsManager.on('reload', syncTeXController.handleReloadMessage as MessageHandler);
wsManager.on('error', syncTeXController.handleErrorMessage as MessageHandler);

/**
 * Update connection status UI
 */
function updateConnectionStatus(connected: boolean): void {
  if (!connectionStatus || !CONFIG.inverse_search_enabled) return;
  
  const status = determineStatus(connected, lifecycle.isPdfChangedPending());
  const state: ConnectionStatusState = {
    status,
    filename: CONFIG.filename,
    mtime: CONFIG.mtime,
    connectionState: wsManager.connectionState as any,
  };
  
  // Update CSS class and content
  connectionStatus.className = `connection-status-indicator ${getStatusClass(status)}`;
  connectionStatus.innerHTML = renderStatusIndicator(state);
  connectionStatus.classList.remove('hidden');
  
  // Update details panel
  updateConnectionDetails(state);
}

/**
 * Update connection details panel content
 */
function updateConnectionDetails(state: ConnectionStatusState): void {
  if (!connectionDetails) return;
  
  connectionDetails.innerHTML = renderDetailsPanel(state);
}

/**
 * Toggle connection details panel visibility
 */
function toggleDetailsPanel(): void {
  if (!connectionDetails) return;
  
  detailsPanelVisible = !detailsPanelVisible;
  if (detailsPanelVisible) {
    connectionDetails.classList.add('visible');
    // Refresh with current state
    const state: ConnectionStatusState = {
      status: determineStatus(wsManager.isConnected, lifecycle.isPdfChangedPending()),
      filename: CONFIG.filename,
      mtime: CONFIG.mtime,
      connectionState: wsManager.connectionState as any,
    };
    updateConnectionDetails(state);
  } else {
    connectionDetails.classList.remove('visible');
  }
}

/**
 * Hide connection details panel
 */
function hideDetailsPanel(): void {
  if (!connectionDetails) return;
  detailsPanelVisible = false;
  connectionDetails.classList.remove('visible');
}

/**
 * Hide connection status indicator
 */
function hideConnectionStatus(): void {
  if (connectionStatus) {
    connectionStatus.classList.add('hidden');
  }
}

// Setup connection status click handler
if (connectionStatus) {
  connectionStatus.addEventListener('click', () => {
    const status = determineStatus(wsManager.isConnected, lifecycle.isPdfChangedPending());
    
    if (status === 'disconnected') {
      // Try to reconnect WebSocket first
      console.log('Reconnecting WebSocket...');
      wsManager.connect();
    } else if (status === 'reload-needed') {
      // PDF has changed - trigger reload
      updateConnectionStatus(true);
      lifecycle.reloadPDF();
    } else {
      // Connected state - toggle details panel
      toggleDetailsPanel();
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
  errorBanner.hide();
});

wsManager.onDisconnect((code) => {
  // Show disconnected state on indicator
  updateConnectionStatus(false);
});

wsManager.onInvalidToken(() => {
  // Server restarted with new token - show disconnected state
  updateConnectionStatus(false);
});

// Show initial connection status only if inverse search is enabled
if (CONFIG.inverse_search_enabled) {
  updateConnectionStatus(false);
}

// Connect to WebSocket
wsManager.connect();

// Create input handler
const inputHandler = createInputHandler(
  {
    viewerContainer,
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
    onLongPress: handleLongPress,
    onClickOutsideTooltip: (clientX, clientY) => {
      if (isClickOutsideTooltip(clientX, clientY)) {
        hideActiveTooltip();
      }
    },
    onClickOutsidePanel: () => {
      hideDetailsPanel();
    },
  },
  getPdfPositionAtPoint
);

// Attach input handler
inputHandler.attach();

// Simple visibility change handler - just reconnects WebSocket
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    viewerContainer.focus();
    lifecycle.syncState();
    
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
    lifecycle.syncState();
    
    setTimeout(() => {
      if (!wsManager.isConnected) {
        wsManager.connect();
      }
    }, 100);
  }
});

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
console.log('Initializing viewer, CONFIG.filename:', CONFIG.filename);
if (CONFIG.filename === 'no-pdf-loaded') {
  console.log('No PDF loaded yet, showing message');
  if (noPdfMessage) {
    noPdfMessage.classList.remove('hidden');
    noPdfMessage.style.display = 'block';
    console.log('Removed hidden class from noPdfMessage');
  } else {
    console.warn('noPdfMessage element not found');
  }
  if (viewerContainer) {
    viewerContainer.classList.add('hidden');
  }
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
