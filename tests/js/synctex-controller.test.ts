import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  createSyncTeXController,
  type SyncTeXControllerOptions,
} from '../../static/synctex-controller';
import type { StateUpdate, WebSocketMessage } from '../../static/types';

describe('SyncTeX Controller', () => {
  let mockOptions: SyncTeXControllerOptions;
  let controller: ReturnType<typeof createSyncTeXController>;

  beforeEach(() => {
    // Setup mock options with initial 'no-pdf-loaded' state
    mockOptions = {
      config: {
        filename: 'no-pdf-loaded',
        mtime: 0,
      },
      stateManager: {
        applyUpdate: vi.fn(),
        isNewerSync: vi.fn().mockReturnValue(false),
        setPdfLoaded: vi.fn(),
        updatePdfMtime: vi.fn(),
        updateSyncTime: vi.fn(),
        pendingUpdate: null,
        setPendingUpdate: vi.fn(),
      } as any,
      pdfRenderer: {
        getCanvas: vi.fn().mockReturnValue({
          style: { height: '800px' },
          height: 800,
        }),
        getPageScale: vi.fn().mockReturnValue(1.5),
        getPageElements: vi.fn().mockReturnValue({}),
        getPageScales: vi.fn().mockReturnValue({}),
        clear: vi.fn(),
      } as any,
      notificationManager: {
        error: vi.fn(),
      } as any,
      onPdfReload: vi.fn().mockResolvedValue(undefined),
      onStatusUpdate: vi.fn(),
      onApplyStateUpdate: vi.fn(),
    };

    // Create controller
    controller = createSyncTeXController(mockOptions);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('handleSyncTeXMessage()', () => {
    it('should return early when no page data', () => {
      const message: WebSocketMessage = {
        action: 'synctex',
        page: undefined,
      };

      // Should not throw
      expect(() => controller.handleSyncTeXMessage(message)).not.toThrow();
      
      // No reload should be triggered
      expect(mockOptions.onPdfReload).not.toHaveBeenCalled();
    });

    it('should handle initial PDF load (no-pdf-loaded)', () => {
      const message: WebSocketMessage = {
        action: 'synctex',
        page: 5,
        pdf_file: 'document.pdf',
        pdf_mtime: 1710508200,
        x: 100,
        y: 200,
        last_sync_time: 1234567890,
      };

      // Simulate initial state
      controller.handleSyncTeXMessage(message);

      // Should trigger PDF reload for initial load
      expect(mockOptions.onPdfReload).toHaveBeenCalled();
    });

    it('should set reload-needed status when PDF file changes', () => {
      const message: WebSocketMessage = {
        action: 'synctex',
        page: 5,
        pdf_file: 'different.pdf',
        pdf_mtime: 1710508200,
        x: 100,
        y: 200,
      };

      // First load
      controller.handleSyncTeXMessage({
        action: 'synctex',
        page: 1,
        pdf_file: 'original.pdf',
        pdf_mtime: 1710000000,
      });

      // Reset mocks
      vi.clearAllMocks();

      // Different PDF file
      controller.handleSyncTeXMessage(message);

      // Should NOT reload immediately, but set status
      expect(mockOptions.onPdfReload).not.toHaveBeenCalled();
      expect(mockOptions.onStatusUpdate).toHaveBeenCalledWith('reload-needed');
    });

    it('should reload when same file modified (mtime changed)', () => {
      const message1: WebSocketMessage = {
        action: 'synctex',
        page: 1,
        pdf_file: 'document.pdf',
        pdf_mtime: 1710000000,
      };

      const message2: WebSocketMessage = {
        action: 'synctex',
        page: 5,
        pdf_file: 'document.pdf',
        pdf_mtime: 1710508200, // Newer mtime
        x: 100,
        y: 200,
      };

      // First load
      controller.handleSyncTeXMessage(message1);
      vi.clearAllMocks();

      // Same file, newer mtime
      controller.handleSyncTeXMessage(message2);

      // Should reload
      expect(mockOptions.onPdfReload).toHaveBeenCalled();
    });

    it('should apply state update when PDF unchanged', () => {
      const message: WebSocketMessage = {
        action: 'synctex',
        page: 5,
        pdf_file: 'document.pdf',
        pdf_mtime: 1710000000,
        x: 100,
        y: 200,
        last_sync_time: 1234567890,
      };

      // First load to set initial state
      controller.handleSyncTeXMessage(message);
      vi.clearAllMocks();

      // Same PDF, same mtime, different position
      controller.handleSyncTeXMessage({
        ...message,
        page: 6,
        x: 150,
        y: 250,
      });

      // Should NOT reload
      expect(mockOptions.onPdfReload).not.toHaveBeenCalled();
      // Should apply state update
      expect(mockOptions.onApplyStateUpdate).toHaveBeenCalled();
    });

    it('should update CONFIG with new filename and mtime', () => {
      const message: WebSocketMessage = {
        action: 'synctex',
        page: 5,
        pdf_file: 'newfile.pdf',
        pdf_mtime: 1710508200,
      };

      controller.handleSyncTeXMessage(message);

      // With initial state 'no-pdf-loaded', this triggers immediate reload
      expect(mockOptions.onPdfReload).toHaveBeenCalled();
    });
  });

  describe('handleReloadMessage()', () => {
    it('should reload PDF when reload message received', () => {
      const message: WebSocketMessage = {
        action: 'reload',
        pdf_file: 'document.pdf',
        pdf_mtime: 1710508200,
      };

      controller.handleReloadMessage(message);

      expect(mockOptions.onPdfReload).toHaveBeenCalled();
    });

    it('should update state manager mtime', () => {
      const message: WebSocketMessage = {
        action: 'reload',
        pdf_mtime: 1710508200,
      };

      controller.handleReloadMessage(message);

      expect(mockOptions.stateManager.updatePdfMtime).toHaveBeenCalledWith(1710508200);
    });

    it('should handle reload without mtime', () => {
      const message: WebSocketMessage = {
        action: 'reload',
      };

      // Should not throw
      expect(() => controller.handleReloadMessage(message)).not.toThrow();
      
      // Should still reload
      expect(mockOptions.onPdfReload).toHaveBeenCalled();
    });
  });

  describe('handleErrorMessage()', () => {
    it('should show error notification', () => {
      const message: WebSocketMessage = {
        action: 'error',
        message: 'Something went wrong',
      };

      controller.handleErrorMessage(message);

      expect(mockOptions.notificationManager.error).toHaveBeenCalledWith('Something went wrong');
    });

    it('should handle error without message', () => {
      const message: WebSocketMessage = {
        action: 'error',
      };

      // Should not throw
      expect(() => controller.handleErrorMessage(message)).not.toThrow();
      
      // Should not call error (no message to show)
      expect(mockOptions.notificationManager.error).not.toHaveBeenCalled();
    });

    it('should log error to console', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      const message: WebSocketMessage = {
        action: 'error',
        message: 'Test error',
      };

      controller.handleErrorMessage(message);

      expect(consoleSpy).toHaveBeenCalledWith('Server error:', 'Test error');
      
      consoleSpy.mockRestore();
    });
  });

  describe('applyStateUpdate()', () => {
    it('should update state manager', () => {
      const stateUpdate: StateUpdate = {
        page: 5,
        x: 100,
        y: 200,
        last_sync_time: 1234567890,
      };

      controller.applyStateUpdate(stateUpdate);

      expect(mockOptions.stateManager.applyUpdate).toHaveBeenCalledWith(stateUpdate);
    });

    it('should call onApplyStateUpdate with correct parameters', () => {
      const stateUpdate: StateUpdate = {
        page: 5,
        x: 100,
        y: 200,
      };

      controller.applyStateUpdate(stateUpdate, 100, 0, true);

      expect(mockOptions.onApplyStateUpdate).toHaveBeenCalledWith(
        expect.any(Object),
        100, // delay
        0, // attempt
        true // isForwardSync
      );
    });

    it('should use default values when not provided', () => {
      const stateUpdate: StateUpdate = {
        page: 5,
      };

      controller.applyStateUpdate(stateUpdate);

      expect(mockOptions.onApplyStateUpdate).toHaveBeenCalledWith(
        expect.any(Object),
        0, // default delay
        0, // default attempt
        false // default isForwardSync
      );
    });
  });

  describe('integration scenarios', () => {
    it('should handle rapid successive sync messages', () => {
      const messages: WebSocketMessage[] = [
        { action: 'synctex', page: 1, pdf_file: 'doc.pdf', pdf_mtime: 1000 },
        { action: 'synctex', page: 2, x: 100, y: 200 },
        { action: 'synctex', page: 3, x: 150, y: 250 },
      ];

      messages.forEach(msg => {
        expect(() => controller.handleSyncTeXMessage(msg)).not.toThrow();
      });
    });

    it('should handle mixed message types', () => {
      // First SyncTeX - initial load
      controller.handleSyncTeXMessage({
        action: 'synctex',
        page: 1,
        pdf_file: 'doc.pdf',
        pdf_mtime: 1000,
      });

      // Error
      controller.handleErrorMessage({
        action: 'error',
        message: 'Warning',
      });

      // Reload
      controller.handleReloadMessage({
        action: 'reload',
        pdf_mtime: 2000,
      });

      // All should work without interference
      // Once for initial load (when filename is 'no-pdf-loaded'), once for reload message
      expect(mockOptions.onPdfReload).toHaveBeenCalledTimes(2);
    });

    it('should handle missing optional fields gracefully', () => {
      const minimalMessage: WebSocketMessage = {
        action: 'synctex',
        page: 1,
      };

      expect(() => controller.handleSyncTeXMessage(minimalMessage)).not.toThrow();
    });
  });
});
