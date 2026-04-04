/**
 * EntangledPdf Viewer - Keyboard Handler
 *
 * Vim-style keyboard navigation for the PDF viewer.
 */

import { LINE_SCROLL_AMOUNT, HORIZONTAL_SCROLL_AMOUNT } from './constants';

/**
 * Handler function type for keyboard commands
 */
export type KeyboardCommandHandler = () => void | Promise<void>;

/**
 * Keyboard command configuration
 */
export interface KeyboardCommand {
  keys: string[];
  handler: KeyboardCommandHandler;
  preventDefault: boolean;
}

/**
 * Keyboard handler options
 */
export interface KeyboardHandlerOptions {
  onScrollDown?: () => void;
  onScrollUp?: () => void;
  onScrollLeft?: () => void;
  onScrollRight?: () => void;
  onNextPage?: () => void;
  onPreviousPage?: () => void;
  onFirstPage?: () => void;
  onLastPage?: () => void;
  onScrollPageDown?: (shiftKey: boolean) => void;
  onInverseSearch?: () => void | Promise<void>;
  isInputFocused?: () => boolean;
}

/**
 * Keyboard handler for PDF viewer navigation
 */
export class KeyboardHandler {
  private options: KeyboardHandlerOptions;
  private boundHandler: (e: KeyboardEvent) => void;
  private isEnabled = true;

  constructor(options: KeyboardHandlerOptions) {
    this.options = options;
    this.boundHandler = this.handleKeydown.bind(this);
  }

  /**
   * Attach the keyboard handler to the document
   * @param useCapture - Use capture phase (true for intercepting before extensions like Vimium)
   */
  attach(useCapture = true): void {
    document.addEventListener('keydown', this.boundHandler, useCapture);
  }

  /**
   * Detach the keyboard handler
   */
  detach(): void {
    document.removeEventListener('keydown', this.boundHandler, true);
    document.removeEventListener('keydown', this.boundHandler, false);
  }

  /**
   * Enable/disable keyboard handling
   */
  set enabled(value: boolean) {
    this.isEnabled = value;
  }

  get enabled(): boolean {
    return this.isEnabled;
  }

  /**
   * Handle keyboard event
   */
  private handleKeydown(event: KeyboardEvent): void {
    if (!this.isEnabled) {
      return;
    }

    const key = event.key;

    // Ignore if user is typing in an input element
    const target = event.target as HTMLElement;
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable ||
      this.options.isInputFocused?.()
    ) {
      return;
    }

    // Define command handlers
    const commands: Record<string, { handler: () => void; preventDefault: boolean }> = {
      // Scrolling
      'j': { handler: () => this.options.onScrollDown?.(), preventDefault: true },
      'ArrowDown': { handler: () => this.options.onScrollDown?.(), preventDefault: true },
      'k': { handler: () => this.options.onScrollUp?.(), preventDefault: true },
      'ArrowUp': { handler: () => this.options.onScrollUp?.(), preventDefault: true },
      'h': { handler: () => this.options.onScrollLeft?.(), preventDefault: true },
      'ArrowLeft': { handler: () => this.options.onScrollLeft?.(), preventDefault: true },
      'l': { handler: () => this.options.onScrollRight?.(), preventDefault: true },
      'ArrowRight': { handler: () => this.options.onScrollRight?.(), preventDefault: true },

      // Page navigation
      'J': { handler: () => this.options.onNextPage?.(), preventDefault: true },
      'PageDown': { handler: () => this.options.onNextPage?.(), preventDefault: true },
      'K': { handler: () => this.options.onPreviousPage?.(), preventDefault: true },
      'PageUp': { handler: () => this.options.onPreviousPage?.(), preventDefault: true },

      // First/last page
      'g': { handler: () => this.options.onFirstPage?.(), preventDefault: true },
      'G': { handler: () => this.options.onLastPage?.(), preventDefault: true },

      // Inverse search
      'i': { handler: () => this.options.onInverseSearch?.(), preventDefault: true },
      'I': { handler: () => this.options.onInverseSearch?.(), preventDefault: true },

      // Space for page scrolling
      ' ': { 
        handler: () => this.options.onScrollPageDown?.(event.shiftKey), 
        preventDefault: true 
      },
    };

    const command = commands[key];
    if (command) {
      if (command.preventDefault) {
        event.preventDefault();
      }
      
      const result = command.handler();
      // Check if result is a Promise (async handler)
      Promise.resolve(result).catch((e: unknown) => console.error('Keyboard command failed:', e));
    }
  }
}

/**
 * Create default keyboard handler with scroll functions
 * @param container - The scroll container
 * @param pageElements - Map of page numbers to elements
 * @param callbacks - Additional callbacks
 */
export function createDefaultKeyboardHandler(
  container: HTMLElement,
  callbacks: {
    scrollBy: (amount: number) => void;
    scrollHorizontally: (amount: number) => void;
    nextPage: () => void;
    prevPage: () => void;
    goToFirstPage: () => void;
    goToLastPage: () => void;
    scrollFullPageDown: () => void;
    scrollFullPageUp: () => void;
    performInverseSearch?: () => void | Promise<void>;
  }
): KeyboardHandler {
  return new KeyboardHandler({
    onScrollDown: () => callbacks.scrollBy(LINE_SCROLL_AMOUNT),
    onScrollUp: () => callbacks.scrollBy(-LINE_SCROLL_AMOUNT),
    onScrollLeft: () => callbacks.scrollHorizontally(-HORIZONTAL_SCROLL_AMOUNT),
    onScrollRight: () => callbacks.scrollHorizontally(HORIZONTAL_SCROLL_AMOUNT),
    onNextPage: callbacks.nextPage,
    onPreviousPage: callbacks.prevPage,
    onFirstPage: callbacks.goToFirstPage,
    onLastPage: callbacks.goToLastPage,
    onScrollPageDown: (shiftKey) => {
      if (shiftKey) {
        callbacks.scrollFullPageUp();
      } else {
        callbacks.scrollFullPageDown();
      }
    },
    onInverseSearch: callbacks.performInverseSearch,
  });
}
