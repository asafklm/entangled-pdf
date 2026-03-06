/**
 * PdfServer Viewer - Tooltip Manager
 *
 * Manages tooltip creation, positioning, and lifecycle.
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
 * Create an inverse search confirmation tooltip
 * @param position - Screen coordinates for the tooltip
 * @param pdfPosition - PDF coordinates
 * @param onConfirm - Callback when user confirms
 * @param onCancel - Callback when user cancels
 * @returns The tooltip element
 */
export function createInverseSearchTooltip(
  position: { clientX: number; clientY: number },
  pdfPosition: PdfPosition,
  onConfirm: () => void,
  onCancel: () => void
): HTMLElement {
  // Remove any existing tooltip
  hideActiveTooltip();

  // Create tooltip container
  const tooltip = document.createElement('div');
  tooltip.className = 'inverse-search-tooltip';
  tooltip.style.cssText = `
    position: fixed;
    left: ${position.clientX}px;
    top: ${position.clientY - 60}px;
    transform: translateX(-50%);
    background: rgba(30, 30, 30, 0.95);
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 14px;
    font-family: sans-serif;
    z-index: 10000;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 200px;
    user-select: none;
    -webkit-user-select: none;
  `;

  // Header
  const header = document.createElement('div');
  header.style.cssText = 'font-weight: bold; margin-bottom: 4px;';
  header.textContent = 'Go to Source?';
  tooltip.appendChild(header);

  // Info text
  const info = document.createElement('div');
  info.style.cssText = 'font-size: 12px; opacity: 0.8; margin-bottom: 4px;';
  info.textContent = `Page ${pdfPosition.page}, coordinates (${Math.round(pdfPosition.x)}, ${Math.round(pdfPosition.y)})`;
  tooltip.appendChild(info);

  // Confirm button
  const confirmButton = document.createElement('button');
  confirmButton.textContent = 'Confirm (Enter)';
  confirmButton.className = 'tooltip-confirm-btn';
  confirmButton.style.cssText = `
    background: #667eea;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    width: 100%;
    margin-top: 4px;
  `;

  confirmButton.addEventListener('click', (e) => {
    e.stopPropagation();
    onConfirm();
  });

  tooltip.appendChild(confirmButton);

  // Store reference
  activeTooltip = tooltip;

  // Add to document
  document.body.appendChild(tooltip);

  // Focus the button
  confirmButton.focus();

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
  tooltip.style.cssText = `
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(234, 179, 8, 0.95);
    color: rgb(66, 32, 6);
    padding: 12px 20px;
    border-radius: 6px;
    font-size: 14px;
    font-family: sans-serif;
    z-index: 10001;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    text-align: center;
    max-width: 400px;
    user-select: none;
    -webkit-user-select: none;
    cursor: pointer;
  `;
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
  feedback.style.cssText = `
    position: fixed;
    left: ${position.clientX}px;
    top: ${position.clientY}px;
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
