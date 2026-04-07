/**
 * Input Handler Module
 *
 * Handles all user input: keyboard navigation, mouse events, touch events.
 * Extracted from viewer.ts for better separation of concerns.
 */

import { KeyboardHandler } from './keyboard-handler.js';
import { LongPressDetector } from './long-press-handler.js';
import type { PdfPosition, ViewportPosition } from './types.js';

/**
 * Callback functions for input events
 */
export interface InputHandlerOptions {
  viewerContainer: HTMLElement;
  onScrollDown: () => void;
  onScrollUp: () => void;
  onScrollLeft: () => void;
  onScrollRight: () => void;
  onNextPage: () => void;
  onPreviousPage: () => void;
  onFirstPage: () => void;
  onLastPage: () => void;
  onScrollPageDown: (shiftKey: boolean) => void;
  onInverseSearch: () => void;
  onLongPress: (position: ViewportPosition, pdfPosition: PdfPosition) => void;
  onClickOutsideTooltip: (clientX: number, clientY: number) => void;
  onClickOutsidePanel: () => void;
}

/**
 * Get PDF position at viewport point
 * This is passed from viewer.ts since it needs pdfRenderer
 */
export type GetPdfPositionFn = (position: ViewportPosition) => PdfPosition | null;

/**
 * Create input handler with all event listeners
 */
export function createInputHandler(
  options: InputHandlerOptions,
  getPdfPositionAtPoint?: GetPdfPositionFn
): {
  attach: () => void;
  detach: () => void;
} {
  // Create keyboard handler
  const keyboardHandler = new KeyboardHandler({
    onScrollDown: options.onScrollDown,
    onScrollUp: options.onScrollUp,
    onScrollLeft: options.onScrollLeft,
    onScrollRight: options.onScrollRight,
    onNextPage: options.onNextPage,
    onPreviousPage: options.onPreviousPage,
    onFirstPage: options.onFirstPage,
    onLastPage: options.onLastPage,
    onScrollPageDown: options.onScrollPageDown,
    onInverseSearch: options.onInverseSearch,
  });

  // Create long press detector (only if position getter is provided)
  let longPressDetector: LongPressDetector | null = null;
  if (getPdfPositionAtPoint) {
    longPressDetector = new LongPressDetector({
      duration: 500,
      moveThreshold: 10,
      onLongPress: options.onLongPress,
      isInteractiveElement: (target) => {
        if (!target) return false;
        const element = target as HTMLElement;
        return element.tagName === 'A' || 
               element.tagName === 'BUTTON' || 
               element.isContentEditable;
      },
    });
  }

  // Get DOM elements for click handling
  const connectionDetails = document.getElementById('connection-details');
  const connectionStatus = document.getElementById('connection-status');

  // Click handler function
  const handleDocumentClick = (event: MouseEvent) => {
    // Focus container when clicking anywhere
    if (document.activeElement !== options.viewerContainer) {
      options.viewerContainer.focus();
    }

    // Notify about click outside tooltip
    options.onClickOutsideTooltip(event.clientX, event.clientY);

    // Check if click is outside connection panel (if elements exist)
    if (connectionDetails && connectionStatus) {
      const target = event.target as HTMLElement;
      if (!connectionDetails.contains(target) && !connectionStatus.contains(target)) {
        options.onClickOutsidePanel();
      }
    }
  };

  // Long press handlers
  let mouseHandlers: ReturnType<LongPressDetector['createMouseHandlers']> | null = null;
  let touchHandlers: ReturnType<LongPressDetector['createTouchHandlers']> | null = null;

  if (longPressDetector && getPdfPositionAtPoint) {
    mouseHandlers = longPressDetector.createMouseHandlers(getPdfPositionAtPoint);
    touchHandlers = longPressDetector.createTouchHandlers(getPdfPositionAtPoint);
  }

  return {
    attach: () => {
      // Attach keyboard handler
      keyboardHandler.attach();

      // Attach long press handlers if available
      if (mouseHandlers && touchHandlers) {
        options.viewerContainer.addEventListener('mousedown', mouseHandlers.onMouseDown);
        options.viewerContainer.addEventListener('mousemove', mouseHandlers.onMouseMove);
        options.viewerContainer.addEventListener('mouseup', mouseHandlers.onMouseUp);
        options.viewerContainer.addEventListener('mouseleave', mouseHandlers.onMouseLeave);

        options.viewerContainer.addEventListener('touchstart', touchHandlers.onTouchStart, { passive: true });
        options.viewerContainer.addEventListener('touchmove', touchHandlers.onTouchMove, { passive: true });
        options.viewerContainer.addEventListener('touchend', touchHandlers.onTouchEnd);
        options.viewerContainer.addEventListener('touchcancel', touchHandlers.onTouchCancel);
      }

      // Attach document click handler
      document.addEventListener('click', handleDocumentClick);
    },

    detach: () => {
      // Detach keyboard handler
      keyboardHandler.detach();

      // Detach long press handlers if available
      if (mouseHandlers && touchHandlers) {
        options.viewerContainer.removeEventListener('mousedown', mouseHandlers.onMouseDown);
        options.viewerContainer.removeEventListener('mousemove', mouseHandlers.onMouseMove);
        options.viewerContainer.removeEventListener('mouseup', mouseHandlers.onMouseUp);
        options.viewerContainer.removeEventListener('mouseleave', mouseHandlers.onMouseLeave);

        options.viewerContainer.removeEventListener('touchstart', touchHandlers.onTouchStart);
        options.viewerContainer.removeEventListener('touchmove', touchHandlers.onTouchMove);
        options.viewerContainer.removeEventListener('touchend', touchHandlers.onTouchEnd);
        options.viewerContainer.removeEventListener('touchcancel', touchHandlers.onTouchCancel);
      }

      // Detach document click handler
      document.removeEventListener('click', handleDocumentClick);
    },
  };
}
