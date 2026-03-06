/**
 * PdfServer Viewer - Marker Manager
 *
 * Handles creation, positioning, and lifecycle of red dot markers.
 */

import { MARKER_DISPLAY_TIME, MARKER_OFFSET } from './constants';
import type { MockCanvas } from './types';
import { pdfYToPixels, pdfToPixelPosition } from './coordinate-utils';

/**
 * Remove all existing markers from the document
 */
export function clearAllMarkers(): void {
  document.querySelectorAll('.synctex-marker').forEach(m => m.remove());
}

/**
 * Create a marker element at the specified Y position
 * @param pixelY - Y position in pixels from top of page
 * @param pixelX - X position in pixels (optional, centered if not provided)
 * @returns The marker element
 */
export function createMarker(pixelY: number, pixelX?: number): HTMLElement {
  const marker = document.createElement('div');
  marker.className = 'synctex-marker';
  
  // Only set inline styles for positioning
  // CSS class provides: left: 5px, width: 10px, height: 10px, etc.
  marker.style.position = 'absolute';
  marker.style.top = `${pixelY - MARKER_OFFSET}px`;
  
  // If x coordinate provided, position horizontally at that point
  // Otherwise, let CSS handle it (defaults to left: 5px from .synctex-marker class)
  if (pixelX != null) {
    marker.style.left = `${pixelX - MARKER_OFFSET}px`;
  }
  
  return marker;
}

/**
 * Show a red dot marker at the specified position on a page
 * @param pageWrapper - The page wrapper element
 * @param pixelY - Y position in pixels
 * @param pixelX - X position in pixels (optional)
 * @param displayTime - Time in ms to show marker (default: 5000ms)
 */
export function showMarker(
  pageWrapper: HTMLElement,
  pixelY: number,
  pixelX?: number,
  displayTime = MARKER_DISPLAY_TIME
): void {
  // Remove existing markers first
  clearAllMarkers();
  
  // Ensure wrapper has relative positioning
  pageWrapper.style.position = 'relative';
  
  // Create and append marker
  const marker = createMarker(pixelY, pixelX);
  pageWrapper.appendChild(marker);
  
  // Auto-remove after display time
  setTimeout(() => marker.remove(), displayTime);
}

/**
 * Show a red dot marker at PDF coordinates
 * @param pageWrapper - The page wrapper element
 * @param canvas - The canvas element for coordinate conversion
 * @param pageScale - The PDF viewport scale for the page
 * @param y - Y coordinate in PDF points (required)
 * @param x - X coordinate in PDF points (optional, centered if not provided)
 * @param displayTime - Time in ms to show marker
 */
export function showMarkerAtPdfCoordinates(
  pageWrapper: HTMLElement,
  canvas: MockCanvas,
  pageScale: number,
  y: number,
  x?: number,
  displayTime = MARKER_DISPLAY_TIME
): void {
  if (y == null) return;
  
  let pixelX: number | undefined;
  
  if (x != null) {
    const { pixelX: px, pixelY: py } = pdfToPixelPosition(canvas, x, y, pageScale);
    pixelX = px;
    showMarker(pageWrapper, py, pixelX, displayTime);
  } else {
    const pixelY = pdfYToPixels(canvas, y, pageScale);
    showMarker(pageWrapper, pixelY, undefined, displayTime);
  }
}

/**
 * Show a red dot marker at a specific page by number
 * @param pageElements - Map of page numbers to wrapper elements
 * @param pageScales - Map of page numbers to PDF scales
 * @param pageNum - The page number
 * @param y - Y coordinate in PDF points
 * @param x - X coordinate in PDF points (optional)
 * @param displayTime - Time in ms to show marker
 */
export function showMarkerAtPage(
  pageElements: { [key: number]: HTMLElement },
  pageScales: { [key: number]: number },
  pageNum: number,
  y: number,
  x?: number,
  displayTime = MARKER_DISPLAY_TIME
): void {
  const pageWrapper = pageElements[pageNum];
  if (!pageWrapper) return;
  
  const canvas = pageWrapper.querySelector('canvas') as MockCanvas | null;
  if (!canvas) return;
  
  const pageScale = pageScales[pageNum] ?? 1.0;
  showMarkerAtPdfCoordinates(pageWrapper, canvas, pageScale, y, x, displayTime);
}
