/**
 * EntangledPdf Viewer - Tooltip Manager
 *
 * Manages tooltip creation, positioning, and lifecycle.
 * Refactored to use declarative CSS classes instead of inline styles.
 */

import { FEEDBACK_DISPLAY_TIME, TOOLTIP_AUTO_HIDE_DELAY } from './constants';
import type { PdfPosition } from './types';

/**
 * Reference to the currently active tooltip
 */
let activeTooltip: HTMLElement | null = null;

/**
 * Get the currently active tooltip element
 */
export function getActiveTooltip(): HTMLElement | null {
  return activeTooltip;
}

/**
 * Hide and remove the active tooltip
 */
export function hideActiveTooltip(): void {
  if (activeTooltip) {
    activeTooltip.remove();
    activeTooltip = null;
  }
}

/**
 * Check if a tooltip is currently visible
 */
export function isTooltipActive(): boolean {
  return activeTooltip !== null;
}

/**
 * Generate tooltip HTML structure
 * Pure function: transforms state into HTML string
 * This pattern maps directly to Lit's html template literal
 */
function renderTooltipHTML(
  pdfPosition: PdfPosition,
  isConnected: boolean
): string {
  const headerText = isConnected ? 'Go to Source?' : 'Authentication Required';
  const buttonText = isConnected ? 'Confirm (Enter)' : 'Re-authenticate';
  const buttonClass = isConnected ? 'tooltip-btn-confirm' : 'tooltip-btn-auth';
  
  const infoText = isConnected
    ? `Page ${pdfPosition.page}, coordinates (${Math.round(pdfPosition.x)}, ${Math.round(pdfPosition.y)})`
    : 'Server restarted. Re-authenticate to use inverse search.';
  
  return `
    <div class="tooltip-header">${headerText}</div>
    <div class="tooltip-info">${infoText}</div>
    <button class="${buttonClass}">${buttonText}</button>
  `;
}

/**
 * Create an inverse search confirmation tooltip
 * @param position - Screen coordinates for the tooltip
 * @param pdfPosition - PDF coordinates
 * @param onConfirm - Callback when user confirms (or re-authenticates if disconnected)
 * @param onCancel - Callback when user cancels
 * @param isConnected - Whether WebSocket is connected (determines button text/action)
 * @returns The tooltip element
 */
export function createInverseSearchTooltip(
  position: { clientX: number; clientY: number },
  pdfPosition: PdfPosition,
  onConfirm: () => void,
  onCancel: () => void,
  isConnected: boolean = true
): HTMLElement {
  // Remove any existing tooltip
  hideActiveTooltip();

  // Create tooltip container
  const tooltip = document.createElement('div');
  tooltip.className = 'inverse-search-tooltip';
  
  // Set position dynamically (only inline styles needed)
  tooltip.style.left = `${position.clientX}px`;
  tooltip.style.top = `${position.clientY - 60}px`;
  
  // Render declarative content
  tooltip.innerHTML = renderTooltipHTML(pdfPosition, isConnected);

  // Setup button click handler
  const actionButton = tooltip.querySelector('button') as HTMLButtonElement;
  actionButton.addEventListener('click', (e) => {
    e.stopPropagation();
    onConfirm();
    hideActiveTooltip();
  });

  // Store reference
  activeTooltip = tooltip;

  // Add to document
  document.body.appendChild(tooltip);

  // Focus the button
  actionButton.focus();

  // Setup keyboard handler
  setupTooltipKeyboardHandler(onConfirm, onCancel);

  return tooltip;
}

/**
 * Setup keyboard handler for the active tooltip
 */
function setupTooltipKeyboardHandler(onConfirm: () => void, onCancel: () => void): void {
  const handler = (e: KeyboardEvent) => {
    if (!isTooltipActive()) {
      document.removeEventListener('keydown', handler, true);
      return;
    }

    if (e.key === 'Enter') {
      e.preventDefault();
      e.stopPropagation();
      onConfirm();
      document.removeEventListener('keydown', handler, true);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      onCancel();
      document.removeEventListener('keydown', handler, true);
    } else {
      // Any other key cancels tooltip and passes through
      hideActiveTooltip();
      document.removeEventListener('keydown', handler, true);
    }
  };

  document.addEventListener('keydown', handler, true);
}

/**
 * Create a sync error tooltip
 * @param message - Error message to display
 * @param autoHide - Whether to auto-hide after delay
 */
export function showSyncError(
  message: string,
  autoHide = true
): void {
  const tooltip = document.createElement('div');
  tooltip.className = 'sync-error-tooltip';
  tooltip.textContent = message;

  // Click to dismiss
  tooltip.addEventListener('click', () => {
    tooltip.remove();
  });

  document.body.appendChild(tooltip);

  // Auto-remove
  if (autoHide) {
    setTimeout(() => {
      tooltip.remove();
    }, TOOLTIP_AUTO_HIDE_DELAY);
  }
}

/**
 * Show visual feedback for inverse search
 * @param position - Screen coordinates
 */
export function showInverseSearchFeedback(position: { clientX: number; clientY: number }): void {
  const feedback = document.createElement('div');
  feedback.className = 'inverse-search-feedback';
  feedback.style.left = `${position.clientX}px`;
  feedback.style.top = `${position.clientY}px`;
  feedback.textContent = 'Inverse search...';
  
  document.body.appendChild(feedback);

  setTimeout(() => {
    feedback.remove();
  }, FEEDBACK_DISPLAY_TIME);
}

/**
 * Check if click is outside the active tooltip
 * @param clientX - Click X coordinate
 * @param clientY - Click Y coordinate
 * @returns true if click is outside tooltip
 */
export function isClickOutsideTooltip(clientX: number, clientY: number): boolean {
  if (!activeTooltip) return true;

  const rect = activeTooltip.getBoundingClientRect();
  return (
    clientX < rect.left ||
    clientX > rect.right ||
    clientY < rect.top ||
    clientY > rect.bottom
  );
}
