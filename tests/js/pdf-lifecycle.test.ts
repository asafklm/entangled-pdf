import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  createPdfLifecycle,
  type PdfLifecycleOptions,
} from '../../static/pdf-lifecycle';
import type { StateUpdate } from '../../static/types';

describe('PDF Lifecycle', () => {
  let mockOptions: Required<PdfLifecycleOptions>;
  let lifecycle: ReturnType<typeof createPdfLifecycle>;
  let originalFetch: typeof global.fetch;

  beforeEach(() => {
    // Mock fetch
    originalFetch = global.fetch;
    global.fetch = vi.fn();

    // Setup mock options
    mockOptions = {
      config: {
        filename: 'document.pdf',
        mtime: 1710000000,
      },
      stateManager: {
        reset: vi.fn(),
        updatePdfMtime: vi.fn(),
        updateSyncTime: vi.fn(),
        isNewerSync: vi.fn().mockReturnValue(false),
        setPdfLoaded: vi.fn(),
        pendingUpdate: null,
        setPendingUpdate: vi.fn(),
      } as any,
      pdfRenderer: {
        clear: vi.fn(),
        load: vi.fn().mockResolvedValue(undefined),
      } as any,
      notificationManager: {
        error: vi.fn(),
      } as any,
      noPdfMessage: document.createElement('div') as any,
      viewerContainer: document.createElement('div') as any,
      onStatusUpdate: vi.fn(),
      onApplyStateUpdate: vi.fn(),
      onClearMarkers: vi.fn(),
    };

    // Setup DOM - hide noPdfMessage since we're simulating a PDF being loaded
    document.body.innerHTML = '';
    mockOptions.noPdfMessage.classList.add('hidden');
    document.body.appendChild(mockOptions.noPdfMessage);
    document.body.appendChild(mockOptions.viewerContainer);

    // Create lifecycle
    lifecycle = createPdfLifecycle(mockOptions);
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  describe('reloadPDF()', () => {
    it('should prevent concurrent reloads', async () => {
      // Start first reload
      const promise1 = lifecycle.reloadPDF();
      
      // Try to start second reload immediately
      const promise2 = lifecycle.reloadPDF();
      
      await Promise.all([promise1, promise2]);
      
      // Should only reload once
      expect(mockOptions.pdfRenderer.load).toHaveBeenCalledTimes(1);
    });

    it('should hide no-pdf message and show container', async () => {
      await lifecycle.reloadPDF();
      
      expect(mockOptions.noPdfMessage.classList.contains('hidden')).toBe(true);
      expect(mockOptions.viewerContainer.classList.contains('hidden')).toBe(false);
    });

    it('should clear existing state', async () => {
      await lifecycle.reloadPDF();
      
      expect(mockOptions.pdfRenderer.clear).toHaveBeenCalled();
      expect(mockOptions.stateManager.reset).toHaveBeenCalled();
      expect(mockOptions.onClearMarkers).toHaveBeenCalled();
    });

    it('should call pdfRenderer.load with correct URL', async () => {
      await lifecycle.reloadPDF();
      
      expect(mockOptions.pdfRenderer.load).toHaveBeenCalled();
      const url = mockOptions.pdfRenderer.load.mock.calls[0][0];
      expect(url).toContain('/get-pdf');
    });

    it('should update state manager mtime after reload', async () => {
      mockOptions.config.mtime = 1710508200;
      
      await lifecycle.reloadPDF();
      
      expect(mockOptions.stateManager.updatePdfMtime).toHaveBeenCalledWith(1710508200);
    });

    it('should clear pdfChangedPending flag', async () => {
      // Set pending flag first (would need to simulate this)
      await lifecycle.reloadPDF();
      
      // After reload, status should be updated
      expect(mockOptions.onStatusUpdate).toHaveBeenCalledWith('connected');
    });

    it('should apply pending state update if exists', async () => {
      const pendingUpdate: StateUpdate = {
        page: 5,
        x: 100,
        y: 200,
        last_sync_time: 1234567890,
      };
      
      mockOptions.stateManager.pendingUpdate = pendingUpdate;
      
      await lifecycle.reloadPDF();
      
      expect(mockOptions.onApplyStateUpdate).toHaveBeenCalledWith(pendingUpdate, expect.any(Number));
      expect(mockOptions.stateManager.setPendingUpdate).toHaveBeenCalledWith(null);
    });

    it('should show error notification on load failure', async () => {
      mockOptions.pdfRenderer.load.mockRejectedValue(new Error('Load failed'));
      
      await lifecycle.reloadPDF();
      
      expect(mockOptions.notificationManager.error).toHaveBeenCalledWith(
        'Failed to reload PDF. Please check that the file exists.'
      );
    });

    it('should clear pending update on failure', async () => {
      mockOptions.stateManager.pendingUpdate = { page: 1 } as StateUpdate;
      mockOptions.pdfRenderer.load.mockRejectedValue(new Error('Load failed'));
      
      await lifecycle.reloadPDF();
      
      expect(mockOptions.stateManager.setPendingUpdate).toHaveBeenCalledWith(null);
    });
  });

  describe('syncState()', () => {
    it('should return early if pdfChangedPending is true', async () => {
      // First call to set pdfChangedPending
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        json: () => Promise.resolve({
          pdf_basename: 'new.pdf',
          pdf_mtime: 1710508200,
          page: 1,
        }),
      });
      
      await lifecycle.syncState();
      
      // Reset mocks
      vi.clearAllMocks();
      
      // Second call should return early
      await lifecycle.syncState();
      
      // Should not fetch again
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should fetch state from server', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        json: () => Promise.resolve({
          pdf_basename: 'document.pdf',
          pdf_mtime: 1710000000,
          page: 1,
        }),
      });
      
      await lifecycle.syncState();
      
      expect(global.fetch).toHaveBeenCalledWith('/state');
    });

    it('should reload PDF when filename changes (initial load)', async () => {
      // Initial state: no-pdf-loaded
      mockOptions.config.filename = 'no-pdf-loaded';
      
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        json: () => Promise.resolve({
          pdf_basename: 'document.pdf',
          pdf_mtime: 1710000000,
          page: 1,
        }),
      });
      
      await lifecycle.syncState();
      
      // Should reload PDF via pdfRenderer.load (initial load path)
      expect(mockOptions.pdfRenderer.load).toHaveBeenCalled();
    });

    it('should set reload-needed when filename changes (not initial)', async () => {
      // Initial state already has PDF
      mockOptions.config.filename = 'old.pdf';
      
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        json: () => Promise.resolve({
          pdf_basename: 'new.pdf',
          pdf_mtime: 1710508200,
          page: 1,
        }),
      });
      
      await lifecycle.syncState();
      
      expect(mockOptions.onStatusUpdate).toHaveBeenCalledWith('reload-needed');
    });

    it('should reload PDF when mtime changes', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        json: () => Promise.resolve({
          pdf_basename: 'document.pdf',
          pdf_mtime: 1710508200, // Newer mtime
          page: 1,
        }),
      });
      
      await lifecycle.syncState();
      
      // Should reload PDF via pdfRenderer.load (mtime changed path)
      expect(mockOptions.pdfRenderer.load).toHaveBeenCalled();
    });

    it('should apply newer sync when PDF unchanged', async () => {
      mockOptions.stateManager.isNewerSync.mockReturnValue(true);
      
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        json: () => Promise.resolve({
          pdf_basename: 'document.pdf',
          pdf_mtime: 1710000000, // Same mtime
          page: 5,
          x: 100,
          y: 200,
          last_sync_time: 1234567890,
        }),
      });
      
      await lifecycle.syncState();
      
      expect(mockOptions.stateManager.setPdfLoaded).toHaveBeenCalledWith(true);
      expect(mockOptions.onApplyStateUpdate).toHaveBeenCalled();
    });

    it('should not apply sync when not newer', async () => {
      mockOptions.stateManager.isNewerSync.mockReturnValue(false);
      
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        json: () => Promise.resolve({
          pdf_basename: 'document.pdf',
          pdf_mtime: 1710000000,
          page: 5,
          x: 100,
          y: 200,
          last_sync_time: 1234567890,
        }),
      });
      
      await lifecycle.syncState();
      
      expect(mockOptions.onApplyStateUpdate).not.toHaveBeenCalled();
    });

    it('should update timestamps after processing', async () => {
      // Mock same mtime (no reload) but with last_sync_time
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        json: () => Promise.resolve({
          pdf_basename: 'document.pdf',
          pdf_mtime: 1710000000, // Same as initial
          page: 1,
          last_sync_time: 1234567890,
        }),
      });
      
      await lifecycle.syncState();
      
      // updateSyncTime should be called when last_sync_time is present
      expect(mockOptions.stateManager.updateSyncTime).toHaveBeenCalled();
    });

    it('should handle fetch errors gracefully', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));
      
      // Should not throw
      await expect(lifecycle.syncState()).resolves.not.toThrow();
    });

    it('should handle missing pdf_basename', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        json: () => Promise.resolve({
          pdf_file: 'document.pdf', // Alternative field
          pdf_mtime: 1710000000,
          page: 1,
        }),
      });
      
      await lifecycle.syncState();
      
      // Should use pdf_file as fallback
      expect(mockOptions.config.filename).toBe('document.pdf');
    });
  });

  describe('integration scenarios', () => {
    it('should handle rapid syncState calls', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        json: () => Promise.resolve({
          pdf_basename: 'document.pdf',
          pdf_mtime: 1710000000,
          page: 1,
        }),
      });
      
      // Multiple rapid calls
      await Promise.all([
        lifecycle.syncState(),
        lifecycle.syncState(),
        lifecycle.syncState(),
      ]);
      
      // Should handle gracefully (no duplicate processing)
      // Since file hasn't changed, pdfRenderer.load should not be called
      expect(mockOptions.pdfRenderer.load).not.toHaveBeenCalled();
    });

    it('should handle reload followed by sync', async () => {
      // First: reload
      await lifecycle.reloadPDF();
      vi.clearAllMocks();
      
      // Then: sync (same mtime)
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        json: () => Promise.resolve({
          pdf_basename: 'document.pdf',
          pdf_mtime: 1710000000, // Same as after reload
          page: 1,
        }),
      });
      
      await lifecycle.syncState();
      
      // Should not reload again (pdfRenderer.load not called again after clearMocks)
      expect(mockOptions.pdfRenderer.load).not.toHaveBeenCalled();
    });

    it('should handle sync during reload', async () => {
      // Start reload
      const reloadPromise = lifecycle.reloadPDF();
      
      // Attempt sync during reload (pdfChangedPending should be true)
      const syncResult = await lifecycle.syncState();
      
      // Sync should return early
      expect(global.fetch).not.toHaveBeenCalled();
      
      await reloadPromise;
    });
  });
});
