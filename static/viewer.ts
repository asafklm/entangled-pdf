/**
 * PdfServer Viewer JavaScript
 *
 * Handles PDF rendering, WebSocket communication, and SyncTeX synchronization.
 */

import type { PDFPageProxy, PDFDocumentProxy } from '../types/pdfjs';

// Initialize PDF.js
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

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
let socket: WebSocket | null = null;
let reconnectAttempts: number = 0;
let pollingInterval: number | null = null;
let lastPage: number | null = null;
let lastY: number | null = null;
let lastUpdateTimestamp: number = 0;

// Configuration from server
interface PDFConfig {
  port: number;
  filename: string;
}

declare global {
  interface Window {
    PDF_CONFIG: PDFConfig;
  }
}

const CONFIG: PDFConfig = window.PDF_CONFIG || { port: 8431, filename: 'document.pdf' };

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
 * @param y - Y coordinate in PDF points
 * @returns Pixel Y coordinate
 */
function pdfYToPixels(canvas: CanvasWithStyle, y: number): number {
  return y * getRenderScale(canvas);
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
    pdfDoc = await pdfjsLib.getDocument('/get-pdf').promise;
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

  const pixelY: number = pdfYToPixels(canvas as CanvasWithStyle, y);

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

  const pixelY: number = pdfYToPixels(canvas as CanvasWithStyle, y);

  const marker: HTMLElement = document.createElement('div');
  marker.className = 'synctex-marker';
  marker.style.top = (pixelY - MARKER_OFFSET) + 'px';

  target.style.position = 'relative';
  target.appendChild(marker);

  setTimeout(() => marker.remove(), MARKER_DISPLAY_TIME);
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
  })
  .catch((error: Error) => {
    console.error("Failed to load PDF:", error);
    if (container) {
      container.innerHTML = '<div style="color: white; padding: 20px; text-align: center;"><h2>Error loading PDF</h2><p>Please check that the PDF file exists and is accessible.</p></div>';
    }
  });
