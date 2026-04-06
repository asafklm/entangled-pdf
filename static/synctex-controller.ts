/**
 * SyncTeX Controller Module
 *
 * Handles SyncTeX synchronization messages from WebSocket.
 * Manages PDF reload decisions and state updates.
 * Extracted from viewer.ts for better separation of concerns.
 */

import type { StateManager } from './state-manager.js';
import type { PDFRenderer } from './pdf-renderer.js';
import type { NotificationManager } from './notification-manager.js';
import type { StateUpdate, WebSocketMessage } from './types.js';

/**
 * Configuration object (from server)
 */
interface ViewerConfig {
  filename: string;
  mtime: number;
}

/**
 * Options for creating SyncTeX controller
 */
export interface SyncTeXControllerOptions {
  config: ViewerConfig;
  stateManager: StateManager;
  pdfRenderer: PDFRenderer;
  notificationManager: NotificationManager;
  onPdfReload: () => Promise<void>;
  onStatusUpdate: (status: 'reload-needed' | 'connected' | 'disconnected') => void;
  onApplyStateUpdate: (
    stateUpdate: StateUpdate,
    delay: number,
    attempt: number,
    isForwardSync: boolean
  ) => void;
}

/**
 * Create SyncTeX controller for handling WebSocket messages
 */
export function createSyncTeXController(options: SyncTeXControllerOptions): {
  handleSyncTeXMessage(data: WebSocketMessage): void;
  handleReloadMessage(data: WebSocketMessage): void;
  handleErrorMessage(data: WebSocketMessage): void;
  applyStateUpdate(data: StateUpdate, delay?: number, attempt?: number, isForwardSync?: boolean): void;
} {
  let pdfChangedPending = false;

  /**
   * Handle SyncTeX message from WebSocket
   */
  function handleSyncTeXMessage(data: WebSocketMessage): void {
    console.log('[handleSyncTeXMessage] Received:', {
      page: data.page,
      pdf_file: data.pdf_file,
      pdf_mtime: data.pdf_mtime,
      action: data.action,
    });

    if (!data.page) {
      console.log('[handleSyncTeXMessage] No page data, returning');
      return;
    }

    // Check if the PDF file has changed in this sync message
    const serverBasename = data.pdf_file;
    const serverMtime = data.pdf_mtime;

    // Capture old values before updating
    const oldFilename = options.config.filename;
    const oldMtime = options.config.mtime;

    console.log('[handleSyncTeXMessage] Change detection:', {
      oldFilename,
      oldMtime,
      serverBasename,
      serverMtime,
      pdfChangedPending_before: pdfChangedPending,
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

    console.log('[handleSyncTeXMessage] Change results:', {
      filenameChanged,
      mtimeChanged,
      'oldFilename === no-pdf-loaded': oldFilename === 'no-pdf-loaded',
    });

    if (filenameChanged) {
      // Different PDF file - show reload button
      // Only exception: initial load (no PDF loaded yet)
      if (oldFilename === 'no-pdf-loaded') {
        console.log('[handleSyncTeXMessage] Initial load - calling reloadPDF()');
        options.onPdfReload();
      } else {
        console.log('[handleSyncTeXMessage] Different PDF - setting pdfChangedPending=true');
        pdfChangedPending = true;
        options.onStatusUpdate('reload-needed');
      }
      return;
    }

    if (mtimeChanged) {
      console.log('[handleSyncTeXMessage] Same file modified - calling reloadPDF()');
      options.onPdfReload();
      return;
    }

    console.log('[handleSyncTeXMessage] PDF unchanged - applying sync position');
    // PDF unchanged - apply the sync position
    applyStateUpdate(
      {
        page: data.page,
        x: data.x,
        y: data.y,
        last_sync_time: data.last_sync_time,
        action: data.action,
      },
      0,
      0,
      true
    );
  }

  /**
   * Handle reload message from WebSocket
   */
  function handleReloadMessage(data: WebSocketMessage): void {
    console.log('[handleReloadMessage] Received:', {
      pdf_file: data.pdf_file,
      pdf_mtime: data.pdf_mtime,
    });

    const reloadMtime = data.pdf_mtime;
    const reloadFilename = data.pdf_file;

    if (reloadMtime && reloadMtime > 0) {
      options.config.mtime = reloadMtime;
      // Update state manager immediately to prevent race condition with syncState
      // This ensures syncState() won't trigger another reload for the same mtime
      options.stateManager.updatePdfMtime(reloadMtime);
    }

    // Update filename if provided (from /api/load-pdf broadcast)
    if (reloadFilename) {
      console.log('[handleReloadMessage] Updating filename:', reloadFilename);
      options.config.filename = reloadFilename;
    }

    options.onPdfReload();
  }

  /**
   * Handle error message from WebSocket
   */
  function handleErrorMessage(data: WebSocketMessage): void {
    const errorMessage = data.message;
    if (errorMessage) {
      console.error('Server error:', errorMessage);
      options.notificationManager.error(errorMessage);
    }
  }

  /**
   * Apply state update
   */
  function applyStateUpdate(
    data: StateUpdate,
    delay = 0,
    attempt = 0,
    isForwardSync = false
  ): void {
    options.stateManager.applyUpdate(data);
    options.onApplyStateUpdate(data, delay, attempt, isForwardSync);
  }

  return {
    handleSyncTeXMessage,
    handleReloadMessage,
    handleErrorMessage,
    applyStateUpdate,
  };
}
