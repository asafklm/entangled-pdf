/**
 * PdfServer Viewer - Testable Module
 *
 * Extracted functions from viewer.js for unit testing
 */

// Constants
export const ACTION_SYNCTEX: string = 'synctex';
export const MAX_RECONNECT_DELAY: number = 30000;
export const POLLING_INTERVAL: number = 2000;
export const MARKER_DISPLAY_TIME: number = 5000;
export const MARKER_OFFSET: number = 5;

/**
 * Canvas element with required style property
 */
interface CanvasWithStyle extends HTMLCanvasElement {
  style: CSSStyleDeclaration;
}

/**
 * Mock canvas interface for testing
 */
export interface MockCanvas {
  style: { height: string };
  height: number;
}

/**
 * State update data structure
 */
export interface StateUpdate {
  page: number;
  y?: number;
  last_sync_time?: number;
}

/**
 * WebSocket message data structure
 */
export interface WebSocketData {
  action?: string;
  page?: number;
  y?: number;
  last_sync_time?: number;
}

/**
 * Calculate render scale from canvas dimensions
 * @param canvas - The canvas element (or mock for testing)
 * @returns Render scale factor
 */
export function getRenderScale(canvas: MockCanvas): number {
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
export function pdfYToPixels(canvas: MockCanvas, y: number, pdfScale: number = 1.0): number {
  // SynTeX reports coordinates in PDF points (1/72 inch) from the TOP of the page
  // This matches CSS/Canvas coordinates which are also from the top
  // At PDF scale 1.0, 1 PDF point = 1 CSS pixel (approximately)
  // At PDF scale 1.5, we multiply by 1.5 to get correct CSS pixels
  const cssPixels: number = y * pdfScale;
  return cssPixels * getRenderScale(canvas);
}

/**
 * Calculate scroll position for a given page and y-coordinate
 * @param container - The scroll container
 * @param target - The target page element
 * @param canvas - The canvas element
 * @param y - Y coordinate in PDF points (from top, SynTeX format)
 * @param pdfScale - The PDF viewport scale used during rendering (default: 1.0)
 * @returns The scroll top position
 */
export function calculateScrollPosition(
  container: HTMLElement,
  target: { offsetTop: number },
  canvas: MockCanvas,
  y: number,
  pdfScale: number = 1.0
): number {
  const pixelY: number = pdfYToPixels(canvas, y, pdfScale);
  const containerStyle: CSSStyleDeclaration = window.getComputedStyle(container);
  const paddingTop: number = parseFloat(containerStyle.paddingTop) || 20;
  const viewportHeight: number = container.clientHeight;
  const targetScrollTop: number = target.offsetTop + pixelY - (viewportHeight / 2) + paddingTop;
  return Math.max(0, Math.round(targetScrollTop));
}

/**
 * Create a marker element at the specified position
 * @param pixelY - Y position in pixels
 * @returns The marker element
 */
export function createMarker(pixelY: number): HTMLElement {
  const marker: HTMLElement = document.createElement('div');
  marker.className = 'synctex-marker';
  marker.style.top = (pixelY - MARKER_OFFSET) + 'px';
  return marker;
}

/**
 * Validate state update data
 * @param data - The state data
 * @returns True if valid
 */
export function isValidStateUpdate(data: unknown): boolean {
  return (
    data !== null &&
    data !== undefined &&
    typeof data === 'object' &&
    'page' in data &&
    typeof (data as StateUpdate).page === 'number' &&
    (data as StateUpdate).page > 0
  );
}

/**
 * Parse WebSocket message data
 * @param message - The raw message data
 * @returns Parsed data or null if invalid
 */
export function parseWebSocketMessage(message: string): WebSocketData | null {
  try {
    return JSON.parse(message) as WebSocketData;
  } catch {
    return null;
  }
}

/**
 * Calculate reconnection delay with exponential backoff
 * @param attempts - Number of reconnection attempts
 * @returns Delay in milliseconds
 */
export function calculateReconnectDelay(attempts: number): number {
  return Math.min(1000 * Math.pow(2, attempts), MAX_RECONNECT_DELAY);
}

/**
 * Check if state update is newer than current
 * @param newData - New state data
 * @param currentTimestamp - Current timestamp
 * @returns True if newer
 */
export function isNewerState(newData: StateUpdate, currentTimestamp: number): boolean {
  const newTimestamp: number = newData.last_sync_time || 0;
  return newTimestamp > currentTimestamp;
}
