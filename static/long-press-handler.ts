/**
 * PdfServer Viewer - Long Press Handler
 *
 * Unified long-press detection for both mouse and touch input.
 */

import type { ViewportPosition, PdfPosition, LongPressState } from './types';
import {
  LONG_PRESS_DURATION_MS,
  LONG_PRESS_MOVE_THRESHOLD,
} from './constants';

/**
 * Handler function type for long press activation
 */
export type LongPressHandler = (position: ViewportPosition, pdfPosition: PdfPosition) => void;

/**
 * Options for the long press detector
 */
export interface LongPressDetectorOptions {
  duration?: number;
  moveThreshold?: number;
  onLongPress: LongPressHandler;
  onStart?: () => void;
  onCancel?: () => void;
  isInteractiveElement?: (element: EventTarget | null) => boolean;
}

/**
 * Long press detector that works with both mouse and touch
 */
export class LongPressDetector {
  private timer: number | null = null;
  private startPos: ViewportPosition | null = null;
  private isActive = false;
  private options: Required<LongPressDetectorOptions>;

  constructor(options: LongPressDetectorOptions) {
    this.options = {
      duration: options.duration ?? LONG_PRESS_DURATION_MS,
      moveThreshold: options.moveThreshold ?? LONG_PRESS_MOVE_THRESHOLD,
      onLongPress: options.onLongPress,
      onStart: options.onStart ?? (() => {}),
      onCancel: options.onCancel ?? (() => {}),
      isInteractiveElement: options.isInteractiveElement ?? (() => false),
    };
  }

  /**
   * Start long press detection
   * @param position - Starting position
   */
  start(position: ViewportPosition): void {
    if (this.isActive) {
      this.cancel();
    }

    this.startPos = position;
    this.isActive = true;
    this.options.onStart();

    this.timer = window.setTimeout(() => {
      this.isActive = false;
      this.timer = null;
      // Long press triggered - handler will be called by the caller with PDF coordinates
    }, this.options.duration);
  }

  /**
   * Update position during long press (check if moved too far)
   * @param position - Current position
   * @returns true if still valid, false if cancelled
   */
  move(position: ViewportPosition): boolean {
    if (!this.isActive || !this.startPos) {
      return false;
    }

    const dx = Math.abs(position.clientX - this.startPos.clientX);
    const dy = Math.abs(position.clientY - this.startPos.clientY);

    if (dx > this.options.moveThreshold || dy > this.options.moveThreshold) {
      this.cancel();
      return false;
    }

    return true;
  }

  /**
   * Cancel the long press
   */
  cancel(): void {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    
    if (this.isActive) {
      this.isActive = false;
      this.options.onCancel();
    }
    
    this.startPos = null;
  }

  /**
   * End the long press (returns true if it was a successful long press)
   * @returns true if long press completed
   */
  end(): boolean {
    const wasActive = this.isActive;
    this.cancel();
    return !wasActive && this.timer === null;
  }

  /**
   * Check if currently detecting a long press
   */
  get isDetecting(): boolean {
    return this.isActive;
  }

  /**
   * Get the start position
   */
  get startPosition(): ViewportPosition | null {
    return this.startPos;
  }

  /**
   * Create event handlers for mouse events
   * @param getPdfPosition - Function to convert screen position to PDF position
   */
  createMouseHandlers(
    getPdfPosition: (pos: ViewportPosition) => PdfPosition | null
  ): {
    onMouseDown: (e: MouseEvent) => void;
    onMouseMove: (e: MouseEvent) => void;
    onMouseUp: () => void;
    onMouseLeave: () => void;
  } {
    return {
      onMouseDown: (e: MouseEvent) => {
        if (this.options.isInteractiveElement(e.target)) {
          return;
        }

        const pos: ViewportPosition = { clientX: e.clientX, clientY: e.clientY };
        this.start(pos);

        // Set up timer callback
        const timer = this.timer;
        if (timer !== null) {
          this.timer = window.setTimeout(() => {
            const pdfPos = getPdfPosition(pos);
            if (pdfPos) {
              this.options.onLongPress(pos, pdfPos);
            }
            this.isActive = false;
            this.timer = null;
          }, this.options.duration);
        }
      },

      onMouseMove: (e: MouseEvent) => {
        const pos: ViewportPosition = { clientX: e.clientX, clientY: e.clientY };
        this.move(pos);
      },

      onMouseUp: () => {
        this.cancel();
      },

      onMouseLeave: () => {
        this.cancel();
      },
    };
  }

  /**
   * Create event handlers for touch events
   * @param getPdfPosition - Function to convert screen position to PDF position
   */
  createTouchHandlers(
    getPdfPosition: (pos: ViewportPosition) => PdfPosition | null
  ): {
    onTouchStart: (e: TouchEvent) => void;
    onTouchMove: (e: TouchEvent) => void;
    onTouchEnd: () => void;
    onTouchCancel: () => void;
  } {
    return {
      onTouchStart: (e: TouchEvent) => {
        if (e.touches.length !== 1) {
          return;
        }

        const touch = e.touches[0];
        const pos: ViewportPosition = { clientX: touch.clientX, clientY: touch.clientY };
        this.start(pos);

        // Set up timer callback
        const timer = this.timer;
        if (timer !== null) {
          this.timer = window.setTimeout(() => {
            const pdfPos = getPdfPosition(pos);
            if (pdfPos) {
              this.options.onLongPress(pos, pdfPos);
            }
            this.isActive = false;
            this.timer = null;
          }, this.options.duration);
        }
      },

      onTouchMove: (e: TouchEvent) => {
        if (e.touches.length !== 1) {
          this.cancel();
          return;
        }

        const touch = e.touches[0];
        const pos: ViewportPosition = { clientX: touch.clientX, clientY: touch.clientY };
        this.move(pos);
      },

      onTouchEnd: () => {
        this.cancel();
      },

      onTouchCancel: () => {
        this.cancel();
      },
    };
  }
}

/**
 * Factory function to create configured long press detector for inverse search
 * @param onLongPress - Handler for when long press is activated
 * @param isEnabled - Function to check if inverse search is enabled
 * @param isInteractiveElement - Function to check if element is interactive
 */
export function createInverseSearchLongPressDetector(
  onLongPress: LongPressHandler,
  isEnabled: () => boolean,
  isInteractiveElement: (element: EventTarget | null) => boolean
): LongPressDetector {
  return new LongPressDetector({
    onLongPress: (pos, pdfPos) => {
      if (isEnabled()) {
        onLongPress(pos, pdfPos);
      }
    },
    isInteractiveElement,
  });
}
