/**
 * PdfServer Viewer - Coordinate Utilities
 *
 * PDF/CSS coordinate conversion utilities.
 */

import type { MockCanvas, PdfPosition, ViewportPosition } from './types';

/**
 * Calculate render scale from canvas dimensions
 * @param canvas - The canvas element (or mock for testing)
 * @returns Render scale factor
 */
export function getRenderScale(canvas: MockCanvas): number {
  const cssHeight = parseFloat(canvas.style.height);
  const internalHeight = canvas.height;
  const dpr = window.devicePixelRatio || 1;
  return (cssHeight * dpr) / internalHeight;
}

/**
 * Convert PDF y-coordinate to CSS pixels
 * @param canvas - The canvas element
 * @param y - Y coordinate in PDF points (from top, SynTeX format)
 * @param pdfScale - The PDF viewport scale used during rendering (default: 1.0)
 * @returns Pixel Y coordinate from top of canvas
 */
export function pdfYToPixels(canvas: MockCanvas, y: number, pdfScale = 1.0): number {
  // SynTeX reports coordinates in PDF points (1/72 inch) from the TOP of the page
  // This matches CSS/Canvas coordinates which are also from the top
  // At PDF scale 1.0, 1 PDF point = 1 CSS pixel (approximately)
  // At PDF scale 1.5, we multiply by 1.5 to get correct CSS pixels
  const cssPixels = y * pdfScale;
  return cssPixels * getRenderScale(canvas);
}

/**
 * Calculate PDF x-coordinate from CSS pixels
 * @param canvas - The canvas element
 * @param pixelX - X position in CSS pixels
 * @param pdfScale - The PDF viewport scale used during rendering (default: 1.0)
 * @returns X coordinate in PDF points
 */
export function pixelsToPdfX(canvas: MockCanvas, pixelX: number, pdfScale = 1.0): number {
  return pixelX / pdfScale / getRenderScale(canvas);
}

/**
 * Calculate PDF y-coordinate from CSS pixels
 * @param canvas - The canvas element
 * @param pixelY - Y position in CSS pixels
 * @param pdfScale - The PDF viewport scale used during rendering (default: 1.0)
 * @returns Y coordinate in PDF points
 */
export function pixelsToPdfY(canvas: MockCanvas, pixelY: number, pdfScale = 1.0): number {
  return pixelY / pdfScale / getRenderScale(canvas);
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
  pdfScale = 1.0
): number {
  const pixelY = pdfYToPixels(canvas, y, pdfScale);
  const containerStyle = window.getComputedStyle(container);
  const paddingTop = parseFloat(containerStyle.paddingTop) || 20;
  const viewportHeight = container.clientHeight;
  const targetScrollTop = target.offsetTop + pixelY - (viewportHeight / 2) + paddingTop;
  return Math.max(0, Math.round(targetScrollTop));
}

/**
 * Calculate pixel position for a PDF coordinate
 * @param canvas - The canvas element
 * @param x - X coordinate in PDF points
 * @param y - Y coordinate in PDF points
 * @param pdfScale - The PDF viewport scale
 * @returns Pixel coordinates
 */
export function pdfToPixelPosition(
  canvas: MockCanvas,
  x: number,
  y: number,
  pdfScale = 1.0
): { pixelX: number; pixelY: number } {
  const pixelX = x * pdfScale * getRenderScale(canvas);
  const pixelY = pdfYToPixels(canvas, y, pdfScale);
  return { pixelX, pixelY };
}

/**
 * Calculate PDF coordinates from a viewport position
 * @param clientX - X coordinate relative to viewport
 * @param clientY - Y coordinate relative to viewport
 * @param targetWrapper - The page wrapper element
 * @param canvas - The canvas element for the page
 * @param pdfScale - The PDF viewport scale
 * @param pageNumber - The page number for the position
 * @returns PDF coordinates or null if calculation fails
 */
export function calculatePdfCoordinatesFromPoint(
  clientX: number,
  clientY: number,
  targetWrapper: HTMLElement,
  canvas: MockCanvas,
  pdfScale = 1.0,
  pageNumber?: number
): PdfPosition | null {
  const wrapperRect = targetWrapper.getBoundingClientRect();
  const relativeX = clientX - wrapperRect.left;
  const relativeY = clientY - wrapperRect.top;

  const x = relativeX / pdfScale;
  const y = relativeY / pdfScale;

  return { x, y, page: pageNumber ?? 0 };
}
