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
const MAX_RECONNECT_DELAY: number = 30000;
const POLLING_INTERVAL: number = 2000;
const MARKER_DISPLAY_TIME: number = 5000;
const MARKER_OFFSET: number = 5; // Center the 10px dot

// DOM Elements
const container: HTMLElement | null = document.getElementById('viewer-container');

// State
let pdfDoc: PDFDocumentProxy | null = null;
const pageElements: { [key: number]: HTMLElement } = {};
const pageScales: { [key: number]: number } = {};
let socket: WebSocket | null = null;
let reconnectAttempts: number = 0;
let pollingInterval: number | null = null;
let lastPage: number | null = null;
let lastY: number | null = null;
let lastUpdateTimestamp: number = 0;

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
}

declare global {
  interface Window {
    PDF_CONFIG: PDFConfig;
  }
}

const CONFIG: PDFConfig = window.PDF_CONFIG || { port: 8431, filename: 'document.pdf', mtime: 0 };

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
 * @param source - Source of the update for logging
 * @param delay - Delay before showing marker (ms)
 */
function applyStateUpdate(data: StateUpdate, source: string, delay: number = 0): void {
  // Update tracking variables
  lastPage = data.page;
  lastY = data.y ?? null;
  if (data.timestamp || data.last_update_time) {
    lastUpdateTimestamp = data.timestamp || data.last_update_time || 0;
  }

  // Scroll to position
  scrollToPage(data.page, data.y);

  // Show marker if y coordinate exists
  if (data.y != null) {
    if (delay > 0) {
      setTimeout(() => showRedDot(data.page, data.y), delay);
    } else {
      showRedDot(data.page, data.y);
    }
  }
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
 * Scroll to a specific page and y-coordinate
 * @param pageNum - Page number to scroll to
 * @param y - Y coordinate in PDF points (optional)
 */
function scrollToPage(pageNum: number, y?: number): void {
  if (!container) {
    console.error('Container not found');
    return;
  }

  const target: HTMLElement | undefined = pageElements[pageNum];
  if (!target) {
    console.error(`Page ${pageNum} not found in pageElements`);
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

  // Handle multi-key sequences first (gg for first page)
  if (key === 'g') {
    if (keyBuffer === 'g') {
      event.preventDefault();
      goToFirstPage();
      resetKeyBuffer();
      return;
    }
    // First 'g' press - set buffer and timeout
    event.preventDefault();
    keyBuffer = 'g';
    if (keyTimeout) clearTimeout(keyTimeout);
    keyTimeout = window.setTimeout(resetKeyBuffer, KEY_TIMEOUT_MS);
    return;
  }

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
    const res: Response = await fetch('/current-state');
    const data: StateUpdate = await res.json();
    console.log("SyncState received:", data);

    if ((data.last_update_time ?? 0) > lastUpdateTimestamp) {
      console.log(`New update detected since last focus: timestamp ${lastUpdateTimestamp}→${data.last_update_time}`);
      applyStateUpdate(data, 'visibility');
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
  }
});

/**
 * Connect to WebSocket server
 */
function connectWebSocket(): void {
  console.log(`Connecting to WebSocket (attempt ${reconnectAttempts + 1})...`);

  socket = new WebSocket(`ws://${window.location.hostname}:${CONFIG.port}/ws`);

  socket.onopen = () => {
    console.log("WebSocket connected");
    reconnectAttempts = 0;
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
      console.log("Stopped polling (WebSocket connected)");
    }
  };

  socket.onmessage = (event: MessageEvent) => {
    const data: StateUpdate = JSON.parse(event.data);
    console.log("WebSocket message received:", data);

    if (data.action === ACTION_SYNCTEX) {
      applyStateUpdate(data, 'websocket', 150);
    }
  };

  socket.onclose = (event: CloseEvent) => {
    console.log(`WebSocket closed (code: ${event.code}, reason: ${event.reason})`);
    socket = null;

    const delay: number = Math.min(1000 * Math.pow(2, reconnectAttempts), MAX_RECONNECT_DELAY);
    reconnectAttempts++;

    console.log(`Reconnecting in ${delay}ms...`);
    setTimeout(connectWebSocket, delay);

    startPolling();
  };

  socket.onerror = (error: Event) => {
    console.error("WebSocket error:", error);
  };
}

/**
 * Start fallback HTTP polling
 */
function startPolling(): void {
  if (pollingInterval) return;

  console.log("Starting fallback polling...");
  pollingInterval = window.setInterval(async () => {
    try {
      const res: Response = await fetch('/current-state');
      const data: StateUpdate = await res.json();

      if ((data.last_update_time ?? 0) > lastUpdateTimestamp) {
        console.log(`Polling detected new update: timestamp ${lastUpdateTimestamp}→${data.last_update_time}`);
        applyStateUpdate(data, 'polling');
      }
    } catch (e) {
      console.error("Polling error:", e);
    }
  }, POLLING_INTERVAL);
}

// Initialize
connectWebSocket();

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

// Focus container when user clicks anywhere on the page (in case they unfocused it)
document.addEventListener('click', () => {
  if (container && document.activeElement !== container) {
    container.focus();
  }
});