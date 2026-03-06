/**
 * PdfServer Viewer JavaScript
 *
 * Handles PDF rendering, WebSocket communication, and SyncTeX synchronization.
 */

// @ts-ignore - Browser module import, resolved at runtime
import * as pdfjsLib from '/pdfjs/pdf.mjs';
import type { PDFPageProxy, PDFDocumentProxy } from '../types/pdfjs';

// Initialize PDF.js with local worker
pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdfjs/pdf.worker.mjs';

// Constants
const ACTION_SYNCTEX: string = 'synctex';
const ACTION_RELOAD: string = 'reload';
const ACTION_INVERSE_SEARCH: string = 'inverse_search';
const MARKER_DISPLAY_TIME: number = 5000;
const MARKER_OFFSET: number = 5; // Center the 10px dot

// DOM Elements
const container: HTMLElement | null = document.getElementById('viewer-container');
const errorBanner: HTMLElement | null = document.getElementById('error-banner');

// State
let pdfDoc: PDFDocumentProxy | null = null;
const pageElements: { [key: number]: HTMLElement } = {};
const pageScales: { [key: number]: number } = {};
let socket: WebSocket | null = null;
let reconnectAttempts: number = 0;
let lastPage: number | null = null;
let lastY: number | null = null;
let lastUpdateTimestamp: number = 0;
let pendingStateUpdate: StateUpdate | null = null;
let lastPdfLoaded: boolean = false;

// Keyboard navigation state
let keyBuffer: string = '';
let keyTimeout: number | null = null;
const KEY_TIMEOUT_MS: number = 500;
const LINE_SCROLL_AMOUNT: number = 40;
const HORIZONTAL_SCROLL_AMOUNT: number = 40;

// Configuration from server
interface PDFConfig {
  port: number;
  filename: string;
  mtime: number;
  token: string | null;
  inverse_search_enabled: boolean;
}

declare global {
  interface Window {
    PDF_CONFIG: PDFConfig;
  }
}

const CONFIG: PDFConfig = window.PDF_CONFIG || { port: 8431, filename: 'document.pdf', mtime: 0, token: null, inverse_search_enabled: false };

/**
 * Canvas element with required style property
 */
interface CanvasWithStyle extends HTMLCanvasElement {
  style: CSSStyleDeclaration;
}

/**
 * State update data structure
 */
interface StateUpdate {
  pdf_loaded?: boolean;
  pdf_file?: string;
  pdf_mtime?: number;
  page: number;
  y?: number;
  timestamp?: number;
  last_update_time?: number;
  action?: string;
}

/**
 * Calculate render scale from canvas dimensions
 * @param canvas - The canvas element
 * @returns Render scale factor
 */
function getRenderScale(canvas: CanvasWithStyle): number {
  const cssHeight: number = parseFloat(canvas.style.height);
  const internalHeight: number = canvas.height;
  const dpr: number = window.devicePixelRatio || 1;
  return (cssHeight * dpr) / internalHeight;
}

/**
 * Convert PDF y-coordinate to CSS pixels
 * @param canvas - The canvas element
 * @param y - Y coordinate in PDF points (from top, SynTeX format)
 * @param pdfScale - The PDF viewport scale used during rendering (default: 1.0)
 * @returns Pixel Y coordinate from top of canvas
 */
function pdfYToPixels(canvas: CanvasWithStyle, y: number, pdfScale: number = 1.0): number {
  // SynTeX reports coordinates in PDF points (1/72 inch) from the TOP of the page
  // This matches CSS/Canvas coordinates which are also from the top
  // At PDF scale 1.0, 1 PDF point = 1 CSS pixel (approximately)
  // At PDF scale 1.5, we multiply by 1.5 to get correct CSS pixels
  const cssPixels: number = y * pdfScale;
  return cssPixels * getRenderScale(canvas);
}

/**
 * Apply state update from any source (WebSocket, polling, or visibility change)
 * @param data - State data with page, y, and timestamp
 * @param delay - Delay before showing marker (ms)
 */
function applyStateUpdate(data: StateUpdate, delay: number = 0): void {
  // Update tracking variables
  lastPage = data.page;
  lastY = data.y ?? null;
  if (data.timestamp || data.last_update_time) {
    lastUpdateTimestamp = data.timestamp || data.last_update_time || 0;
  }

  // Scroll to position and show red dot if y coordinate exists
  // Both scroll and marker are handled together to ensure page is ready
  scrollToPage(data.page, data.y, 0, data.y != null, delay);
}

/**
 * Load and render the PDF document
 */
async function loadPDF(): Promise<void> {
  if (!container) {
    throw new Error('Viewer container not found');
  }

  try {
    const pdfUrl = `/get-pdf?v=${CONFIG.mtime}`;
    pdfDoc = await pdfjsLib.getDocument(pdfUrl).promise;
  } catch (error) {
    throw new Error(`Failed to load PDF document: ${(error as Error).message}`);
  }

  container.innerHTML = '';
  const dpr: number = window.devicePixelRatio || 1;

  if (!pdfDoc) {
    throw new Error('PDF document not loaded');
  }

  for (let i: number = 1; i <= pdfDoc.numPages; i++) {
    const page: PDFPageProxy = await pdfDoc.getPage(i);
    const containerWidth: number = container.clientWidth - 40;

    const pageWidthAt1x: number = page.getViewport({ scale: 1.0 }).width;
    const fitScale: number = containerWidth / pageWidthAt1x;
    const scale: number = Math.max(1.5, fitScale);

    const viewport = page.getViewport({ scale: scale });

    // Store the scale for this page for coordinate conversion
    pageScales[i] = scale;

    const wrapper: HTMLElement = document.createElement('div');
    wrapper.className = 'page-wrapper';

    const canvas: HTMLCanvasElement = document.createElement('canvas');
    const context: CanvasRenderingContext2D | null = canvas.getContext('2d');

    if (!context) {
      throw new Error('Failed to get 2D context from canvas');
    }

    const canvasWidth: number = Math.round(viewport.width * dpr);
    const canvasHeight: number = Math.round(viewport.height * dpr);

    canvas.width = canvasWidth;
    canvas.height = canvasHeight;
    canvas.style.width = Math.round(viewport.width) + 'px';
    canvas.style.height = Math.round(viewport.height) + 'px';

    wrapper.appendChild(canvas);
    container.appendChild(wrapper);

    const transform: number[] | null = dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : null;

    await page.render({
      canvasContext: context,
      viewport: viewport,
      transform: transform
    }).promise;

    pageElements[i] = wrapper;
  }
}

/**
 * Reload the PDF document (clears state and reloads)
 */
async function reloadPDF(): Promise<void> {
  // Hide no-pdf message and show container
  const noPdfMessage = document.getElementById('no-pdf-message');
  if (noPdfMessage) {
    noPdfMessage.style.display = 'none';
  }
  if (container) {
    container.style.display = 'block';
    container.innerHTML = '';
  }
  
  // Clear existing state
  pdfDoc = null;
  for (const key in pageElements) {
    delete pageElements[key];
  }
  for (const key in pageScales) {
    delete pageScales[key];
  }
  lastPage = null;
  lastY = null;
  
  // CONFIG.mtime should already be set by the caller (WebSocket handler)
  // using the pdf_mtime from the broadcast message
  
  // Reload
  try {
    await loadPDF();
    console.log("PDF reloaded successfully");
    
    // Check if there's a pending state update from WebSocket
    if (pendingStateUpdate) {
      console.log("Applying pending sync after PDF reload:", pendingStateUpdate);
      applyStateUpdate(pendingStateUpdate, 150);
      pendingStateUpdate = null;
    } else {
      scrollToPage(1);  // Reset to page 1 when PDF changes
    }
  } catch (error) {
    console.error("Failed to reload PDF:", error);
    pendingStateUpdate = null;  // Clear pending update on error
    if (container) {
      container.innerHTML = '<div style="color: white; padding: 20px; text-align: center;"><h2>Error reloading PDF</h2><p>Please check that the PDF file exists and is accessible.</p></div>';
    }
  }
}

/**
 * Scroll to a specific page and y-coordinate
 * @param pageNum - Page number to scroll to
 * @param y - Y coordinate in PDF points (optional)
 */
function scrollToPage(pageNum: number, y?: number, attempt: number = 0, showMarker: boolean = false, markerDelay: number = 0): void {
  if (!container) {
    console.error('Container not found');
    return;
  }

  const target: HTMLElement | undefined = pageElements[pageNum];
  if (!target) {
    // Retry up to 10 times with 100ms delay - page may still be rendering
    if (attempt < 10) {
      console.log(`Page ${pageNum} not found, retrying... (${attempt + 1}/10)`);
      setTimeout(() => scrollToPage(pageNum, y, attempt + 1, showMarker, markerDelay), 100);
      return;
    }
    console.error(`Page ${pageNum} not found in pageElements after ${attempt} retries`);
    return;
  }

  if (y == null) {
    console.log(`Scrolling to page ${pageNum} (no y coordinate)`);
    target.scrollIntoView({ block: 'start' });
    return;
  }

  const canvas: HTMLCanvasElement | null = target.querySelector('canvas');
  if (!canvas) {
    console.error(`Canvas not found for page ${pageNum}`);
    return;
  }

  const pdfScale: number = pageScales[pageNum] || 1.0;
  const pixelY: number = pdfYToPixels(canvas as CanvasWithStyle, y, pdfScale);

  const containerStyle: CSSStyleDeclaration = window.getComputedStyle(container);
  const paddingTop: number = parseFloat(containerStyle.paddingTop) || 20;

  const viewportHeight: number = container.clientHeight;
  const targetScrollTop: number = target.offsetTop + pixelY - (viewportHeight / 2) + paddingTop;
  const finalScrollTop: number = Math.max(0, Math.round(targetScrollTop));

  console.log(`Scrolling to page ${pageNum}, y=${y}, pixelY=${pixelY}, finalScrollTop=${finalScrollTop}`);

  // Force layout recalculation for Safari
  void container.offsetHeight;

  // Perform scroll with retry logic for Safari compatibility
  container.scrollTo({ top: finalScrollTop, left: 0, behavior: 'auto' });

  // Verify scroll worked, retry if needed
  setTimeout(() => {
    const diff: number = Math.abs(container.scrollTop - finalScrollTop);
    if (diff > 5) {
      console.log(`Scroll retry: diff=${diff}`);
      container.scrollTop = finalScrollTop;
    }
  }, 50);

  // Show red dot marker if requested
  if (showMarker && y != null) {
    if (markerDelay > 0) {
      setTimeout(() => showRedDot(pageNum, y), markerDelay);
    } else {
      showRedDot(pageNum, y);
    }
  }
}

/**
 * Show a red dot marker at the specified position
 * @param pageNum - Page number
 * @param y - Y coordinate in PDF points
 */
function showRedDot(pageNum: number, y?: number): void {
  const target: HTMLElement | undefined = pageElements[pageNum];
  if (!target || y == null) return;

  // Remove existing markers
  document.querySelectorAll('.synctex-marker').forEach(m => m.remove());

  const canvas: HTMLCanvasElement | null = target.querySelector('canvas');
  if (!canvas) return;

  const pdfScale: number = pageScales[pageNum] || 1.0;
  const pixelY: number = pdfYToPixels(canvas as CanvasWithStyle, y, pdfScale);

  const marker: HTMLElement = document.createElement('div');
  marker.className = 'synctex-marker';
  marker.style.top = (pixelY - MARKER_OFFSET) + 'px';

  target.style.position = 'relative';
  target.appendChild(marker);

  setTimeout(() => marker.remove(), MARKER_DISPLAY_TIME);
}

/**
 * Scroll by a number of lines
 * @param amount - Number of pixels to scroll (positive = down, negative = up)
 */
function scrollByLines(amount: number): void {
  if (!container) return;
  const targetScrollTop: number = container.scrollTop + amount;
  container.scrollTo({ top: targetScrollTop, left: container.scrollLeft, behavior: 'auto' });
}

/**
 * Scroll horizontally
 * @param amount - Number of pixels to scroll (positive = right, negative = left)
 */
function scrollHorizontally(amount: number): void {
  if (!container) return;
  const targetScrollLeft: number = container.scrollLeft + amount;
  container.scrollTo({ top: container.scrollTop, left: targetScrollLeft, behavior: 'auto' });
}

/**
 * Navigate to the next page
 */
function nextPage(): void {
  if (!pdfDoc || !lastPage) return;
  const targetPage: number = Math.min(lastPage + 1, pdfDoc.numPages);
  scrollToPage(targetPage);
}

/**
 * Navigate to the previous page
 */
function prevPage(): void {
  if (!pdfDoc || !lastPage) return;
  const targetPage: number = Math.max(lastPage - 1, 1);
  scrollToPage(targetPage);
}

/**
 * Navigate to the first page
 */
function goToFirstPage(): void {
  if (!pdfDoc) return;
  scrollToPage(1);
}

/**
 * Navigate to the last page
 */
function goToLastPage(): void {
  if (!pdfDoc) return;
  scrollToPage(pdfDoc.numPages);
}

/**
 * Scroll a full page down (90% of viewport)
 */
function scrollFullPageDown(): void {
  if (!container) return;
  const viewportHeight: number = container.clientHeight;
  const amount: number = Math.round(viewportHeight * 0.9);
  scrollByLines(amount);
}

/**
 * Scroll a full page up (90% of viewport)
 */
function scrollFullPageUp(): void {
  if (!container) return;
  const viewportHeight: number = container.clientHeight;
  const amount: number = -Math.round(viewportHeight * 0.9);
  scrollByLines(amount);
}

/**
 * Reset the key buffer and clear timeout
 */
function resetKeyBuffer(): void {
  keyBuffer = '';
  if (keyTimeout) {
    clearTimeout(keyTimeout);
    keyTimeout = null;
  }
}

/**
 * Handle keyboard navigation events
 * @param event - Keyboard event
 */
function handleKeydown(event: KeyboardEvent): void {
  const key: string = event.key;

  // If we get here with a key buffer, reset it (sequence broken)
  if (keyBuffer) {
    resetKeyBuffer();
  }

  // Single key actions
  switch (key) {
    case 'j':
    case 'ArrowDown':
      event.preventDefault();
      scrollByLines(LINE_SCROLL_AMOUNT);
      break;

    case 'k':
    case 'ArrowUp':
      event.preventDefault();
      scrollByLines(-LINE_SCROLL_AMOUNT);
      break;

    case 'h':
    case 'ArrowLeft':
      event.preventDefault();
      scrollHorizontally(-HORIZONTAL_SCROLL_AMOUNT);
      break;

    case 'l':
    case 'ArrowRight':
      event.preventDefault();
      scrollHorizontally(HORIZONTAL_SCROLL_AMOUNT);
      break;

    case 'J':
    case 'PageDown':
      event.preventDefault();
      nextPage();
      break;

    case 'K':
    case 'PageUp':
      event.preventDefault();
      prevPage();
      break;

    case ' ':
      event.preventDefault();
      if (event.shiftKey) {
        scrollFullPageUp();
      } else {
        scrollFullPageDown();
      }
      break;

    case 'g':
      event.preventDefault();
      goToFirstPage();
      break;

    case 'G':
      event.preventDefault();
      goToLastPage();
      break;

    default:
      // Don't prevent default for unhandled keys
      return;
  }
}

/**
 * Synchronize state when tab regains focus
 */
async function syncState(): Promise<void> {
  try {
    const res: Response = await fetch("/state");
    const data: StateUpdate = await res.json();
    console.log("SyncState received:", data);

    // Check if PDF became available for the first time or changed
    const pdfBecameAvailable = data.pdf_loaded && !lastPdfLoaded;
    const pdfFileChanged = data.pdf_file && data.pdf_file !== CONFIG.filename;

    if (pdfBecameAvailable || pdfFileChanged) {
      console.log(`PDF change detected: becameAvailable=${pdfBecameAvailable}, fileChanged=${pdfFileChanged}`);

      // Update tracking variables
      lastPdfLoaded = data.pdf_loaded || false;
      if (data.pdf_file) {
        CONFIG.filename = data.pdf_file;
      }
      if (data.pdf_mtime) {
        CONFIG.mtime = data.pdf_mtime;
      }

      // Store as pending and reload
      pendingStateUpdate = { ...data };
      await reloadPDF();
      return;
    }

    // Normal case: just scroll if there is a new update
    if ((data.last_update_time ?? 0) > lastUpdateTimestamp) {
      console.log(`New update detected since last focus: timestamp ${lastUpdateTimestamp}→${data.last_update_time}`);
      applyStateUpdate(data);
    } else {
      console.log("No new updates since last focus, skipping scroll");
    }
  } catch (e) {
    console.error("Sync error", e);
  }
}

// Handle visibility changes
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    console.log("Welcome back! Checking for updates...");
    syncState();
    // Reconnect WebSocket if disconnected with a small delay to prevent race conditions
    setTimeout(() => {
      if (!socket || socket.readyState === WebSocket.CLOSED || socket.readyState === WebSocket.CLOSING) {
        console.log("Reconnecting WebSocket after tab focus...");
        connectWebSocket();
      }
    }, 100);
  }
});

// Handle pageshow event for Android back-forward cache restoration
window.addEventListener("pageshow", (event: PageTransitionEvent) => {
  if (event.persisted) {
    console.log("Page restored from back-forward cache (Android)");
    syncState();
    // Force WebSocket reconnection on page restoration with delay
    setTimeout(() => {
      if (!socket || socket.readyState === WebSocket.CLOSED || socket.readyState === WebSocket.CLOSING) {
        connectWebSocket();
      }
    }, 100);
  }
});

/**
 * Show/hide error banner
 */
function showErrorBanner(message: string): void {
  if (errorBanner) {
    errorBanner.textContent = message;
    errorBanner.style.display = 'block';
  }
}

function hideErrorBanner(): void {
  if (errorBanner) {
    errorBanner.style.display = 'none';
  }
}

/**
 * Connect to WebSocket server
 */
function connectWebSocket(): void {
  // Prevent duplicate connections - check if already connecting or connected
  if (socket && (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN)) {
    console.log('WebSocket already connecting or connected, skipping');
    return;
  }
  
  // If socket exists but is closing/closed, clean it up first
  if (socket) {
    try {
      socket.close();
    } catch (e) {
      // Ignore errors on close
    }
    socket = null;
  }
  
  console.log('Connecting to WebSocket...');

  // Build WebSocket URL with token if available
  let wsUrl = `wss://${window.location.hostname}:${CONFIG.port}/ws`;
  if (CONFIG.token) {
    wsUrl += `?token=${encodeURIComponent(CONFIG.token)}`;
  }

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log('WebSocket connected');
    hideErrorBanner();
  };

  socket.onmessage = (event: MessageEvent) => {
    const data: StateUpdate = JSON.parse(event.data);
    console.log('WebSocket message received:', data);
    
    // Handle ping/pong for connection keepalive
    if (data.action === 'ping') {
      socket?.send(JSON.stringify({ action: 'pong' }));
      return;
    } else if (data.action === 'pong') {
      // Server responded to our ping, connection is alive
      return;
    }

    if (data.action === ACTION_SYNCTEX) {
      applyStateUpdate(data, 150);
    } else if (data.action === ACTION_RELOAD) {
      console.log('Reload requested');
      // Extract pdf_mtime from reload message for cache busting
      const reloadMtime = (data as any).pdf_mtime;
      if (reloadMtime && reloadMtime > 0) {
        console.log(`Reload with pdf_mtime: ${reloadMtime}`);
        CONFIG.mtime = reloadMtime;
      }
      reloadPDF();
    }
  };

  socket.onclose = (event: CloseEvent) => {
    console.log(`WebSocket closed (code: ${event.code})`);
    socket = null;
    
    // Don't show error for clean closures (1000) or going away (1001)
    if (event.code !== 1000 && event.code !== 1001) {
      showErrorBanner(`WebSocket disconnected (code: ${event.code}). Tab refocus or refresh to reconnect.`);
    }
  };

  socket.onerror = (error: Event) => {
    console.error('WebSocket error:', error);
    // Set socket to null so visibilitychange/pageshow handlers will reconnect
    socket = null;
    showErrorBanner('WebSocket connection error. Tab refocus or refresh to reconnect.');
  };
}

/**
 * Calculate PDF coordinates from click position
 * @param event - Mouse click event
 * @returns Object with page number, x, y coordinates in PDF points, or null if calculation fails
 */
function calculatePdfCoordinates(event: MouseEvent): { page: number; x: number; y: number } | null {
  if (!container || !pdfDoc) {
    return null;
  }

  // Find which page was clicked
  let targetPage: number | null = null;
  let targetWrapper: HTMLElement | null = null;

  for (let i = 1; i <= pdfDoc.numPages; i++) {
    const wrapper = pageElements[i];
    if (wrapper) {
      const rect = wrapper.getBoundingClientRect();
      if (event.clientY >= rect.top && event.clientY <= rect.bottom) {
        targetPage = i;
        targetWrapper = wrapper;
        break;
      }
    }
  }

  if (!targetPage || !targetWrapper) {
    return null;
  }

  // Get the canvas for this page
  const canvas = targetWrapper.querySelector('canvas') as CanvasWithStyle | null;
  if (!canvas) {
    return null;
  }

  // Calculate click position relative to the canvas
  const wrapperRect = targetWrapper.getBoundingClientRect();
  const relativeX = event.clientX - wrapperRect.left;
  const relativeY = event.clientY - wrapperRect.top;

  // Get the PDF scale used for this page
  const pdfScale: number = pageScales[targetPage] || 1.0;

  // Convert CSS pixels to PDF points
  // At PDF scale 1.0, 1 PDF point = 1 CSS pixel (approximately)
  const x: number = relativeX / pdfScale;
  const y: number = relativeY / pdfScale;

  return { page: targetPage, x, y };
}

/**
 * Send inverse search request to server
 * @param page - Page number
 * @param x - X coordinate in PDF points
 * @param y - Y coordinate in PDF points
 */
function sendInverseSearch(page: number, x: number, y: number): void {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    console.warn('WebSocket not connected, cannot send inverse search');
    return;
  }

  if (!CONFIG.inverse_search_enabled) {
    console.warn('Inverse search not enabled');
    return;
  }

  const message = {
    action: ACTION_INVERSE_SEARCH,
    page: page,
    x: x,
    y: y
  };

  console.log('Sending inverse search:', message);
  socket.send(JSON.stringify(message));
}

/**
 * Handle shift+click for inverse search
 * @param event - Mouse event
 */
function handleShiftClick(event: MouseEvent): void {
  // Only trigger on shift+click
  if (!event.shiftKey) {
    return;
  }

  // Don't trigger if clicking on interactive elements
  const target = event.target as HTMLElement;
  if (target.tagName === 'A' || target.tagName === 'BUTTON' || target.isContentEditable) {
    return;
  }

  const coords = calculatePdfCoordinates(event);
  if (coords) {
    sendInverseSearch(coords.page, coords.x, coords.y);
    
    // Show visual feedback
    showInverseSearchFeedback(event.clientX, event.clientY);
  }
}

/**
 * Show visual feedback for inverse search
 * @param x - Screen X coordinate
 * @param y - Screen Y coordinate
 */
function showInverseSearchFeedback(x: number, y: number): void {
  const feedback = document.createElement('div');
  feedback.style.cssText = `
    position: fixed;
    left: ${x}px;
    top: ${y}px;
    transform: translate(-50%, -50%);
    background: rgba(102, 126, 234, 0.9);
    color: white;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 12px;
    font-family: sans-serif;
    pointer-events: none;
    z-index: 10000;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  `;
  feedback.textContent = 'Inverse search...';
  document.body.appendChild(feedback);

  // Remove after 1 second
  setTimeout(() => {
    feedback.remove();
  }, 1000);
}

// Initialize
connectWebSocket();

// Check if a PDF is loaded (filename from server)
if (CONFIG.filename === 'no-pdf-loaded') {
  console.log("No PDF loaded yet");
  const noPdfMessage = document.getElementById('no-pdf-message');
  if (noPdfMessage) {
    noPdfMessage.style.display = 'block';
  }
  if (container) {
    container.style.display = 'none';
  }
} else {
  lastPdfLoaded = true;  // Track that PDF is loaded
  loadPDF()
    .then(() => {
      console.log("PDF loaded successfully");
      syncState();
      // Attach keyboard handler after PDF loads and container is ready
      if (container) {
        container.addEventListener('keydown', handleKeydown);
        // Auto-focus container so user doesn't need to click
        container.focus();
        console.log("Keyboard navigation ready (container focused)");
      }
    })
    .catch((error: Error) => {
      console.error("Failed to load PDF:", error);
      if (container) {
        container.innerHTML = '<div style="color: white; padding: 20px; text-align: center;"><h2>Error loading PDF</h2><p>Please check that the PDF file exists and is accessible.</p></div>';
      }
    });
}

// Focus container when user clicks anywhere on the page (in case they unfocused it)
// Also handle shift+click for inverse search
document.addEventListener('click', (event: MouseEvent) => {
  if (container && document.activeElement !== container) {
    container.focus();
  }
  
  // Handle shift+click for inverse search
  if (CONFIG.inverse_search_enabled && event.shiftKey) {
    handleShiftClick(event);
  }
});
