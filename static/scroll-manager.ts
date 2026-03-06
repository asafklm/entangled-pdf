/**
 * PdfServer Viewer - Scroll Manager
 *
 * Handles scrolling with retry logic and Safari compatibility.
 */

import { clearAllMarkers } from './marker-manager';
import type { ScrollOptions } from './types';
import {
  MAX_SCROLL_ATTEMPTS,
  SCROLL_RETRY_DELAY,
  SCROLL_VERIFY_DELAY,
  SCROLL_THRESHOLD,
  MARKER_DELAY_AFTER_RELOAD,
} from './constants';

/**
 * Position information for scroll logging
 */
export interface ScrollPosition {
  page: number;
  y: number;
  pixels: number;
}

/**
 * Callback type for before/after scroll hooks
 */
export type ScrollCallback = (from: ScrollPosition, to: ScrollPosition) => void;

/**
 * Calculate scroll position for a target page element
 * @param container - The scroll container
 * @param target - The target page element
 * @param pixelY - Y position in pixels from top of page
 * @returns The target scroll top position
 */
export function calculateScrollTop(
  container: HTMLElement,
  target: HTMLElement,
  pixelY: number
): number {
  const containerStyle = window.getComputedStyle(container);
  const paddingTop = parseFloat(containerStyle.paddingTop) || 20;
  const viewportHeight = container.clientHeight;
  const targetScrollTop = target.offsetTop + pixelY - (viewportHeight / 2) + paddingTop;
  return Math.max(0, Math.round(targetScrollTop));
}

/**
 * Get current scroll position from container
 */
export function getCurrentScrollPosition(
  container: HTMLElement,
  pageElements: { [key: number]: HTMLElement }
): ScrollPosition | null {
  const scrollTop = container.scrollTop;
  
  // Find which page we're on
  let currentPage = 1;
  for (const [pageNum, element] of Object.entries(pageElements)) {
    const page = parseInt(pageNum);
    if (element.offsetTop <= scrollTop) {
      currentPage = page;
    }
  }
  
  const target = pageElements[currentPage];
  if (!target) {
    return null;
  }
  
  // Calculate offset within page
  const offsetInPage = scrollTop - target.offsetTop;
  
  return {
    page: currentPage,
    y: offsetInPage,
    pixels: scrollTop,
  };
}

/**
 * Calculate target position for scroll
 */
export function getTargetScrollPosition(
  container: HTMLElement,
  pageElements: { [key: number]: HTMLElement },
  pageNum: number,
  pixelY?: number
): ScrollPosition | null {
  const target = pageElements[pageNum];
  if (!target) {
    return null;
  }
  
  let targetScrollTop: number;
  let finalY: number;
  
  if (pixelY == null) {
    // Scroll to page start
    targetScrollTop = target.offsetTop;
    finalY = 0;
  } else {
    // Scroll to specific position
    targetScrollTop = calculateScrollTop(container, target, pixelY);
    finalY = pixelY;
  }
  
  return {
    page: pageNum,
    y: finalY,
    pixels: targetScrollTop,
  };
}

/**
 * Perform scroll with Safari compatibility and verification
 * @param container - The scroll container
 * @param scrollTop - Target scroll position
 * @param behavior - Scroll behavior ('auto' or 'smooth')
 */
export function performScroll(
  container: HTMLElement,
  scrollTop: number,
  behavior: ScrollBehavior = 'auto'
): void {
  // Force layout recalculation for Safari
  void container.offsetHeight;

  // Perform scroll
  container.scrollTo({ top: scrollTop, left: 0, behavior });

  // Verify scroll worked, retry if needed (Safari compatibility)
  setTimeout(() => {
    const diff = Math.abs(container.scrollTop - scrollTop);
    if (diff > SCROLL_THRESHOLD) {
      container.scrollTop = scrollTop;
    }
  }, SCROLL_VERIFY_DELAY);
}

/**
 * Scroll to a page with retry logic for when the page isn't rendered yet
 * @param container - The scroll container
 * @param pageElements - Map of page numbers to elements
 * @param pageNum - Target page number
 * @param pixelY - Y position in pixels (optional, page start if not provided)
 * @param attempt - Current retry attempt
 * @param behavior - Scroll behavior
 * @param onBeforeScroll - Optional callback before scroll (for logging)
 * @returns true if scroll was performed, false if retry scheduled
 */
export function scrollToPageWithRetry(
  container: HTMLElement,
  pageElements: { [key: number]: HTMLElement },
  pageNum: number,
  pixelY?: number,
  attempt = 0,
  behavior: ScrollBehavior = 'auto',
  onBeforeScroll?: ScrollCallback
): boolean {
  const target = pageElements[pageNum];
  
  if (!target) {
    // Retry up to MAX_SCROLL_ATTEMPTS times - page may still be rendering
    if (attempt < MAX_SCROLL_ATTEMPTS) {
      console.log(`Page ${pageNum} not found, retrying... (${attempt + 1}/${MAX_SCROLL_ATTEMPTS})`);
      setTimeout(() => {
        scrollToPageWithRetry(container, pageElements, pageNum, pixelY, attempt + 1, behavior, onBeforeScroll);
      }, SCROLL_RETRY_DELAY);
      return false;
    }
    console.error(`Page ${pageNum} not found after ${MAX_SCROLL_ATTEMPTS} retries`);
    return false;
  }

  // Get "from" position before scrolling
  const fromPosition = onBeforeScroll ? getCurrentScrollPosition(container, pageElements) : null;

  if (pixelY == null) {
    // Just scroll to the page start
    target.scrollIntoView({ block: 'start', behavior });
    
    // Log if callback provided
    if (onBeforeScroll && fromPosition) {
      const toPosition: ScrollPosition = {
        page: pageNum,
        y: 0,
        pixels: target.offsetTop,
      };
      onBeforeScroll(fromPosition, toPosition);
    }
    
    return true;
  }

  // Calculate and perform scroll to specific position
  const scrollTop = calculateScrollTop(container, target, pixelY);
  performScroll(container, scrollTop, behavior);
  
  // Log if callback provided
  if (onBeforeScroll && fromPosition) {
    const toPosition: ScrollPosition = {
      page: pageNum,
      y: pixelY,
      pixels: scrollTop,
    };
    onBeforeScroll(fromPosition, toPosition);
  }
  
  return true;
}

/**
 * Scroll by a number of pixels
 * @param container - The scroll container
 * @param amount - Number of pixels to scroll (positive = down, negative = up)
 * @param behavior - Scroll behavior
 */
export function scrollBy(
  container: HTMLElement,
  amount: number,
  behavior: ScrollBehavior = 'auto'
): void {
  const targetScrollTop = container.scrollTop + amount;
  container.scrollTo({ top: targetScrollTop, left: container.scrollLeft, behavior });
}

/**
 * Scroll horizontally by a number of pixels
 * @param container - The scroll container
 * @param amount - Number of pixels to scroll (positive = right, negative = left)
 * @param behavior - Scroll behavior
 */
export function scrollHorizontallyBy(
  container: HTMLElement,
  amount: number,
  behavior: ScrollBehavior = 'auto'
): void {
  const targetScrollLeft = container.scrollLeft + amount;
  container.scrollTo({ top: container.scrollTop, left: targetScrollLeft, behavior });
}

/**
 * Scroll a full page (90% of viewport height)
 * @param container - The scroll container
 * @param direction - Direction to scroll ('up' or 'down')
 */
export function scrollFullPage(
  container: HTMLElement,
  direction: 'up' | 'down'
): void {
  const viewportHeight = container.clientHeight;
  const amount = Math.round(viewportHeight * 0.9) * (direction === 'up' ? -1 : 1);
  scrollBy(container, amount);
}

/**
 * Navigate to next page
 * @param container - The scroll container
 * @param pageElements - Map of page numbers to elements
 * @param currentPage - Current page number
 * @param totalPages - Total number of pages
 * @returns The new page number, or null if couldn't navigate
 */
export function navigateToNextPage(
  container: HTMLElement,
  pageElements: { [key: number]: HTMLElement },
  currentPage: number | null,
  totalPages: number
): number | null {
  if (!currentPage) return null;
  const targetPage = Math.min(currentPage + 1, totalPages);
  return scrollToPageWithRetry(container, pageElements, targetPage) ? targetPage : null;
}

/**
 * Navigate to previous page
 * @param container - The scroll container
 * @param pageElements - Map of page numbers to elements
 * @param currentPage - Current page number
 * @returns The new page number, or null if couldn't navigate
 */
export function navigateToPreviousPage(
  container: HTMLElement,
  pageElements: { [key: number]: HTMLElement },
  currentPage: number | null
): number | null {
  if (!currentPage) return null;
  const targetPage = Math.max(currentPage - 1, 1);
  return scrollToPageWithRetry(container, pageElements, targetPage) ? targetPage : null;
}

/**
 * Navigate to first or last page
 * @param container - The scroll container
 * @param pageElements - Map of page numbers to elements
 * @param targetPage - Target page number
 * @returns The page number if successful, null otherwise
 */
export function navigateToPage(
  container: HTMLElement,
  pageElements: { [key: number]: HTMLElement },
  targetPage: number
): number | null {
  return scrollToPageWithRetry(container, pageElements, targetPage) ? targetPage : null;
}

/**
 * Get the upper viewport position (25% down from top)
 * @param container - The scroll container
 * @returns The Y position from top of viewport
 */
export function getUpperViewportY(container: HTMLElement): number {
  const viewportHeight = container.clientHeight;
  return Math.max(100, viewportHeight / 4);
}
