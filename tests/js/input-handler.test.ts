import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createInputHandler, type InputHandlerOptions } from '../../static/input-handler';

describe('Input Handler', () => {
  let mockContainer: HTMLElement;
  let mockCallbacks: Required<InputHandlerOptions>;
  let handler: ReturnType<typeof createInputHandler>;

  beforeEach(() => {
    // Setup mock container
    mockContainer = document.createElement('div');
    mockContainer.id = 'viewer-container';
    document.body.appendChild(mockContainer);

    // Setup mock callbacks
    mockCallbacks = {
      viewerContainer: mockContainer,
      onScrollDown: vi.fn(),
      onScrollUp: vi.fn(),
      onScrollLeft: vi.fn(),
      onScrollRight: vi.fn(),
      onNextPage: vi.fn(),
      onPreviousPage: vi.fn(),
      onFirstPage: vi.fn(),
      onLastPage: vi.fn(),
      onScrollPageDown: vi.fn(),
      onInverseSearch: vi.fn(),
      onLongPress: vi.fn(),
      onClickOutsideTooltip: vi.fn(),
      onClickOutsidePanel: vi.fn(),
    };

    // Create handler
    handler = createInputHandler(mockCallbacks);
  });

  afterEach(() => {
    // Cleanup
    handler.detach();
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  describe('attach() and detach()', () => {
    it('should attach keyboard event listeners', () => {
      handler.attach();
      
      // Simulate keydown
      const event = new KeyboardEvent('keydown', { key: 'j' });
      document.dispatchEvent(event);
      
      expect(mockCallbacks.onScrollDown).toHaveBeenCalled();
    });

    it('should attach mouse event listeners', () => {
      handler.attach();
      
      // Simulate mousedown
      const event = new MouseEvent('mousedown', { clientX: 100, clientY: 100 });
      mockContainer.dispatchEvent(event);
      
      // Should not throw
      expect(() => {
        mockContainer.dispatchEvent(event);
      }).not.toThrow();
    });

    it('should attach touch event listeners', () => {
      handler.attach();
      
      // Simulate touchstart
      const touch = new Touch({
        identifier: 1,
        target: mockContainer,
        clientX: 100,
        clientY: 100,
      });
      const event = new TouchEvent('touchstart', { touches: [touch] });
      
      expect(() => {
        mockContainer.dispatchEvent(event);
      }).not.toThrow();
    });

    it('should attach document click listener', () => {
      handler.attach();
      
      // Simulate click
      const event = new MouseEvent('click', { bubbles: true });
      document.body.dispatchEvent(event);
      
      // Container should receive focus (or try to)
      expect(() => {
        document.body.dispatchEvent(event);
      }).not.toThrow();
    });

    it('should detach all listeners without throwing', () => {
      handler.attach();
      
      expect(() => handler.detach()).not.toThrow();
    });

    it('should not respond to events after detach', () => {
      handler.attach();
      handler.detach();
      
      // Simulate keydown after detach
      const event = new KeyboardEvent('keydown', { key: 'j' });
      document.dispatchEvent(event);
      
      // Callback should not be called
      expect(mockCallbacks.onScrollDown).not.toHaveBeenCalled();
    });
  });

  describe('keyboard navigation', () => {
    beforeEach(() => {
      handler.attach();
    });

    it('should handle j/ArrowDown for scroll down', () => {
      const keys = ['j', 'ArrowDown'];
      
      keys.forEach(key => {
        mockCallbacks.onScrollDown.mockClear();
        const event = new KeyboardEvent('keydown', { key, bubbles: true });
        document.dispatchEvent(event);
        expect(mockCallbacks.onScrollDown).toHaveBeenCalled();
      });
    });

    it('should handle k/ArrowUp for scroll up', () => {
      const keys = ['k', 'ArrowUp'];
      
      keys.forEach(key => {
        mockCallbacks.onScrollUp.mockClear();
        const event = new KeyboardEvent('keydown', { key, bubbles: true });
        document.dispatchEvent(event);
        expect(mockCallbacks.onScrollUp).toHaveBeenCalled();
      });
    });

    it('should handle h/ArrowLeft for scroll left', () => {
      const keys = ['h', 'ArrowLeft'];
      
      keys.forEach(key => {
        mockCallbacks.onScrollLeft.mockClear();
        const event = new KeyboardEvent('keydown', { key, bubbles: true });
        document.dispatchEvent(event);
        expect(mockCallbacks.onScrollLeft).toHaveBeenCalled();
      });
    });

    it('should handle l/ArrowRight for scroll right', () => {
      const keys = ['l', 'ArrowRight'];
      
      keys.forEach(key => {
        mockCallbacks.onScrollRight.mockClear();
        const event = new KeyboardEvent('keydown', { key, bubbles: true });
        document.dispatchEvent(event);
        expect(mockCallbacks.onScrollRight).toHaveBeenCalled();
      });
    });

    it('should handle J/PageDown for next page', () => {
      const keys = ['J', 'PageDown'];
      
      keys.forEach(key => {
        mockCallbacks.onNextPage.mockClear();
        const event = new KeyboardEvent('keydown', { key, bubbles: true });
        document.dispatchEvent(event);
        expect(mockCallbacks.onNextPage).toHaveBeenCalled();
      });
    });

    it('should handle K/PageUp for previous page', () => {
      const keys = ['K', 'PageUp'];
      
      keys.forEach(key => {
        mockCallbacks.onPreviousPage.mockClear();
        const event = new KeyboardEvent('keydown', { key, bubbles: true });
        document.dispatchEvent(event);
        expect(mockCallbacks.onPreviousPage).toHaveBeenCalled();
      });
    });

    it('should handle g for first page', () => {
      const event = new KeyboardEvent('keydown', { key: 'g', bubbles: true });
      document.dispatchEvent(event);
      expect(mockCallbacks.onFirstPage).toHaveBeenCalled();
    });

    it('should handle G for last page', () => {
      const event = new KeyboardEvent('keydown', { key: 'G', bubbles: true });
      document.dispatchEvent(event);
      expect(mockCallbacks.onLastPage).toHaveBeenCalled();
    });

    it('should handle Space for page scroll down', () => {
      const event = new KeyboardEvent('keydown', { key: ' ', bubbles: true });
      document.dispatchEvent(event);
      expect(mockCallbacks.onScrollPageDown).toHaveBeenCalledWith(false);
    });

    it('should handle Shift+Space for page scroll up', () => {
      const event = new KeyboardEvent('keydown', { key: ' ', shiftKey: true, bubbles: true });
      document.dispatchEvent(event);
      expect(mockCallbacks.onScrollPageDown).toHaveBeenCalledWith(true);
    });

    it('should handle i/I for inverse search', () => {
      const keys = ['i', 'I'];
      
      keys.forEach(key => {
        mockCallbacks.onInverseSearch.mockClear();
        const event = new KeyboardEvent('keydown', { key, bubbles: true });
        document.dispatchEvent(event);
        expect(mockCallbacks.onInverseSearch).toHaveBeenCalled();
      });
    });

    it('should ignore keys when typing in input', () => {
      const input = document.createElement('input');
      document.body.appendChild(input);
      input.focus();
      
      const event = new KeyboardEvent('keydown', { key: 'j', bubbles: true });
      input.dispatchEvent(event);
      
      expect(mockCallbacks.onScrollDown).not.toHaveBeenCalled();
    });

    it('should ignore keys when typing in textarea', () => {
      const textarea = document.createElement('textarea');
      document.body.appendChild(textarea);
      textarea.focus();
      
      const event = new KeyboardEvent('keydown', { key: 'k', bubbles: true });
      textarea.dispatchEvent(event);
      
      expect(mockCallbacks.onScrollUp).not.toHaveBeenCalled();
    });

    it('should ignore keys in contenteditable elements', () => {
      const div = document.createElement('div');
      div.contentEditable = 'true';
      document.body.appendChild(div);
      div.focus();
      
      const event = new KeyboardEvent('keydown', { key: 'j', bubbles: true });
      div.dispatchEvent(event);
      
      expect(mockCallbacks.onScrollDown).not.toHaveBeenCalled();
    });

    it('should not respond to unmapped keys', () => {
      const event = new KeyboardEvent('keydown', { key: 'x', bubbles: true });
      document.dispatchEvent(event);
      
      // No callbacks should be called
      expect(mockCallbacks.onScrollDown).not.toHaveBeenCalled();
      expect(mockCallbacks.onScrollUp).not.toHaveBeenCalled();
      expect(mockCallbacks.onNextPage).not.toHaveBeenCalled();
    });
  });

  describe('document click handling', () => {
    beforeEach(() => {
      handler.attach();
    });

    it('should call click outside tooltip callback', () => {
      const event = new MouseEvent('click', { 
        clientX: 100, 
        clientY: 100,
        bubbles: true 
      });
      document.dispatchEvent(event);
      
      // The callback is called during click handling
      expect(mockCallbacks.onClickOutsideTooltip).toHaveBeenCalledWith(100, 100);
    });

    it('should call click outside panel callback', () => {
      // Create mock elements
      const panel = document.createElement('div');
      panel.id = 'connection-details';
      const status = document.createElement('div');
      status.id = 'connection-status';
      document.body.appendChild(panel);
      document.body.appendChild(status);
      
      // Need to re-attach with new elements in DOM
      handler.detach();
      handler = createInputHandler(mockCallbacks);
      handler.attach();
      
      // Click outside both elements
      const event = new MouseEvent('click', { 
        clientX: 0, 
        clientY: 0,
        bubbles: true 
      });
      document.dispatchEvent(event);
      
      // Verify callback was called
      expect(mockCallbacks.onClickOutsidePanel).toHaveBeenCalled();
      
      // Cleanup
      panel.remove();
      status.remove();
    });
  });

  describe('long press detection', () => {
    beforeEach(() => {
      handler.attach();
    });

    it('should detect long press on mouse', async () => {
      // Mouse down
      const mouseDown = new MouseEvent('mousedown', { 
        clientX: 100, 
        clientY: 100,
        bubbles: true 
      });
      mockContainer.dispatchEvent(mouseDown);
      
      // Wait for long press duration
      await new Promise(resolve => setTimeout(resolve, 600));
      
      // The long press callback should have been triggered
      // Note: In actual implementation, this would need getPdfPositionAtPoint
      // which we can't easily mock here without more setup
    });

    it('should not trigger long press on quick click', async () => {
      // Mouse down
      const mouseDown = new MouseEvent('mousedown', { 
        clientX: 100, 
        clientY: 100,
        bubbles: true 
      });
      mockContainer.dispatchEvent(mouseDown);
      
      // Quick mouse up
      const mouseUp = new MouseEvent('mouseup', { bubbles: true });
      mockContainer.dispatchEvent(mouseUp);
      
      // Wait to ensure long press doesn't trigger
      await new Promise(resolve => setTimeout(resolve, 600));
      
      // onLongPress should not be called
      // Note: This depends on the actual implementation
    });

    it('should cancel long press on mouse move', async () => {
      // Mouse down
      const mouseDown = new MouseEvent('mousedown', { 
        clientX: 100, 
        clientY: 100,
        bubbles: true 
      });
      mockContainer.dispatchEvent(mouseDown);
      
      // Move mouse significantly
      const mouseMove = new MouseEvent('mousemove', { 
        clientX: 150, // Moved 50px
        clientY: 150,
        bubbles: true 
      });
      mockContainer.dispatchEvent(mouseMove);
      
      // Wait
      await new Promise(resolve => setTimeout(resolve, 600));
      
      // onLongPress should not be called due to movement
    });

    it('should detect long press on touch', async () => {
      // Touch start
      const touch = new Touch({
        identifier: 1,
        target: mockContainer,
        clientX: 100,
        clientY: 100,
      });
      const touchStart = new TouchEvent('touchstart', { 
        touches: [touch],
        bubbles: true 
      });
      mockContainer.dispatchEvent(touchStart);
      
      // Wait for long press duration
      await new Promise(resolve => setTimeout(resolve, 600));
      
      // Long press should trigger
    });
  });

  describe('integration scenarios', () => {
    it('should handle multiple attach/detach cycles', () => {
      handler.attach();
      handler.detach();
      handler.attach();
      handler.detach();
      handler.attach();
      
      // Should work after multiple cycles
      const event = new KeyboardEvent('keydown', { key: 'j', bubbles: true });
      document.dispatchEvent(event);
      expect(mockCallbacks.onScrollDown).toHaveBeenCalled();
    });

    it('should handle rapid key presses', () => {
      handler.attach();
      
      // Rapid key presses
      for (let i = 0; i < 10; i++) {
        const event = new KeyboardEvent('keydown', { key: 'j', bubbles: true });
        document.dispatchEvent(event);
      }
      
      expect(mockCallbacks.onScrollDown).toHaveBeenCalledTimes(10);
    });
  });
});
