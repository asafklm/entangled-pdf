/**
 * PDF Lifecycle Module
 *
 * Handles PDF reloading and state synchronization.
 * Manages the lifecycle of PDF document loading and updates.
 * Extracted from viewer.ts for better separation of concerns.
 */

import type { PDFRenderer } from './pdf-renderer.js';
import type { StateManager } from './state-manager.js';
import type { NotificationManager } from './notification-manager.js';
import type { StateUpdate } from './types.js';
import { MARKER_DELAY_AFTER_RELOAD } from './constants.js';

/**
 * Viewer configuration interface
 */
interface ViewerConfig {
  filename: string;
  mtime: number;
}

/**
 * Options for creating PDF lifecycle manager
 */
export interface PdfLifecycleOptions {
  config: ViewerConfig;
  stateManager: StateManager;
  pdfRenderer: PDFRenderer;
  notificationManager: NotificationManager;
  noPdfMessage: HTMLElement | null;
  viewerContainer: HTMLElement;
  onStatusUpdate: (status: 'reload-needed' | 'connected' | 'disconnected') => void;
  onApplyStateUpdate: (data: StateUpdate, delay: number) => void;
  onClearMarkers: () => void;
}

/**
 * PDF Lifecycle manager interface
 */
export interface PdfLifecycleManager {
  reloadPDF(): Promise<void>;
  syncState(): Promise<void>;
  isPdfChangedPending(): boolean;
  setPdfChangedPending(value: boolean): void;
  isLoading(): boolean;
}

/**
 * Create PDF lifecycle manager
 */
export function createPdfLifecycle(options: PdfLifecycleOptions): PdfLifecycleManager {
  let isLoadingPDF = false;
  let pdfChangedPending = false;

  /**
   * Reload the PDF document
   */
  async function reloadPDF(): Promise<void> {
    // Prevent concurrent reloads - Safari iPad fires multiple events that can trigger reload
    if (isLoadingPDF) {
      console.log('[reloadPDF] PDF reload already in progress, skipping duplicate request');
      return;
    }

    isLoadingPDF = true;

    try {
      // Hide no-pdf message and show container
      if (options.noPdfMessage) {
        options.noPdfMessage.classList.add('hidden');
        options.noPdfMessage.style.display = 'none';
      }
      options.viewerContainer.classList.remove('hidden');

      // Clear existing state
      options.pdfRenderer.clear();
      options.stateManager.reset();
      options.onClearMarkers();

      // Load PDF
      const timestamp = options.config.mtime;
      const url = `/get-pdf?t=${timestamp}`;
      await options.pdfRenderer.load(url);

      // Log PDF load (console only, not business logic)
      console.log('[reloadPDF] PDF loaded:', options.config.filename, options.config.mtime);

      // Clear PDF changed flag since we've reloaded
      pdfChangedPending = false;
      options.onStatusUpdate('connected');

      // Update state manager with new PDF mtime to prevent showing reload button again
      options.stateManager.updatePdfMtime(options.config.mtime);

      // Apply pending state update if exists (from syncState during reload)
      const pending = options.stateManager.pendingUpdate;
      if (pending) {
        options.onApplyStateUpdate(pending, MARKER_DELAY_AFTER_RELOAD);
        options.stateManager.setPendingUpdate(null);
      }
      // Don't scroll to page 1 - let user stay where they are
    } catch (error) {
      console.error('Failed to reload PDF:', error);
      options.stateManager.setPendingUpdate(null);
      options.notificationManager.error('Failed to reload PDF. Please check that the file exists.');
    } finally {
      isLoadingPDF = false;
    }
  }

  /**
   * Synchronize state when tab regains focus or reconnects
   */
  async function syncState(): Promise<void> {
    console.log('[syncState] Starting, pdfChangedPending:', pdfChangedPending);

    // If reload is already in progress, don't duplicate the action
    if (isLoadingPDF) {
      console.log('[syncState] PDF reload in progress, returning early');
      return;
    }

    // If reload already detected this change, don't duplicate the action
    if (pdfChangedPending) {
      console.log('[syncState] pdfChangedPending is true, returning early');
      return;
    }

    try {
      const res = await fetch('/state');
      const data: StateUpdate = await res.json();

      console.log('[syncState] Received state:', {
        pdf_basename: data.pdf_basename,
        pdf_file: data.pdf_file,
        pdf_mtime: data.pdf_mtime,
      });

      // Get server values
      const serverBasename = data.pdf_basename || data.pdf_file;
      const serverMtime = data.pdf_mtime;

      // Capture old values before updating
      const oldFilename = options.config.filename;
      const oldMtime = options.config.mtime;

      console.log('[syncState] Change detection:', {
        oldFilename,
        oldMtime,
        serverBasename,
        serverMtime,
      });

      // Always update CONFIG with new values
      if (serverBasename) {
        options.config.filename = serverBasename;
      }
      if (serverMtime) {
        options.config.mtime = serverMtime;
      }

      // Determine what changed
      const filenameChanged = serverBasename && serverBasename !== oldFilename;
      const mtimeChanged = serverMtime && serverMtime !== oldMtime;

      console.log('[syncState] Change results:', {
        filenameChanged,
        mtimeChanged,
        'oldFilename === no-pdf-loaded': oldFilename === 'no-pdf-loaded',
      });

      if (filenameChanged) {
        // Different PDF file
        // Check if this is the initial PDF load (no PDF loaded yet)
        const noPdfShowing = options.noPdfMessage && !options.noPdfMessage.classList.contains('hidden');
        if (noPdfShowing || oldFilename === 'no-pdf-loaded') {
          console.log('[syncState] Initial load or no PDF showing - calling reloadPDF()');
          pdfChangedPending = true;
          await reloadPDF();
        } else {
          console.log('[syncState] Different PDF - setting pdfChangedPending=true');
          pdfChangedPending = true;
          options.onStatusUpdate('reload-needed');
        }

        // Always update stateManager so we don't detect same change again
        if (serverMtime) {
          options.stateManager.updatePdfMtime(serverMtime);
        }
        return;
      }

      if (mtimeChanged) {
        console.log('[syncState] Same file modified - calling reloadPDF()');
        pdfChangedPending = true;
        await reloadPDF();

        // Update stateManager
        if (serverMtime) {
          options.stateManager.updatePdfMtime(serverMtime);
        }
        return;
      }

      // PDF unchanged - check for newer forward sync to apply
      const newSync = options.stateManager.isNewerSync(data);
      console.log('[syncState] PDF unchanged, newSync:', newSync);

      if (newSync) {
        console.log('[syncState] Applying newer sync position');
        options.stateManager.setPdfLoaded(true);
        options.onApplyStateUpdate(data, 0);
      }

      // Update our tracked timestamps
      if (serverMtime) {
        options.stateManager.updatePdfMtime(serverMtime);
      }
      if (data.last_sync_time) {
        options.stateManager.updateSyncTime(data);
      }
    } catch (e) {
      console.error('[syncState] Error:', e);
    }
  }

  return {
    reloadPDF,
    syncState,
    isPdfChangedPending: () => pdfChangedPending,
    setPdfChangedPending: (value: boolean) => { pdfChangedPending = value; },
    isLoading: () => isLoadingPDF,
  };
}
