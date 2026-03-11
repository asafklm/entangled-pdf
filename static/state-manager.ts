/**
 * PdfServer Viewer - State Manager
 *
 * Centralized viewer state management.
 */

import type { StateUpdate, ViewerState, PDFConfig } from './types';

/**
 * State change listener
 */
export type StateChangeListener = (state: ViewerState) => void;

/**
 * State manager for the PDF viewer
 */
export class StateManager {
  private state: ViewerState;
  private listeners: Set<StateChangeListener> = new Set();

  constructor(initialState?: Partial<ViewerState>) {
    this.state = {
      page: initialState?.page ?? null,
      y: initialState?.y ?? null,
      pdfMtime: initialState?.pdfMtime ?? 0,
      lastSyncTime: initialState?.lastSyncTime ?? 0,
      pdfLoaded: initialState?.pdfLoaded ?? false,
      pendingUpdate: initialState?.pendingUpdate ?? null,
    };
  }

  /**
   * Get current state
   */
  get currentState(): ViewerState {
    return { ...this.state };
  }

  /**
   * Get current page
   */
  get currentPage(): number | null {
    return this.state.page;
  }

  /**
   * Get current Y position
   */
  get currentY(): number | null {
    return this.state.y;
  }

  /**
   * Get last PDF modification time
   */
  get pdfMtime(): number {
    return this.state.pdfMtime;
  }

  /**
   * Get last sync (forward search) time
   */
  get lastSyncTime(): number {
    return this.state.lastSyncTime;
  }

  /**
   * Check if PDF is loaded
   */
  get isPdfLoaded(): boolean {
    return this.state.pdfLoaded;
  }

  /**
   * Get pending update
   */
  get pendingUpdate(): StateUpdate | null {
    return this.state.pendingUpdate;
  }

  /**
   * Subscribe to state changes
   * @returns Unsubscribe function
   */
  subscribe(listener: StateChangeListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Update position and timestamps
   */
  updatePosition(page: number, y?: number, timestamp?: number): void {
    this.state.page = page;
    this.state.y = y ?? null;
    if (timestamp !== undefined) {
      this.state.lastSyncTime = timestamp;
    }
    this.notifyListeners();
  }

  /**
   * Update sync timestamp from state update
   */
  updateSyncTime(data: StateUpdate): void {
    const newSyncTime = data.last_sync_time ?? 0;
    if (newSyncTime > this.state.lastSyncTime) {
      this.state.lastSyncTime = newSyncTime;
      this.notifyListeners();
    }
  }

  /**
   * Update PDF modification time
   */
  updatePdfMtime(mtime: number): void {
    if (mtime > this.state.pdfMtime) {
      this.state.pdfMtime = mtime;
      this.notifyListeners();
    }
  }

  /**
   * Check if a sync (forward search) is newer than current
   */
  isNewerSync(data: StateUpdate): boolean {
    const newSyncTime = data.last_sync_time ?? 0;
    return newSyncTime > this.state.lastSyncTime;
  }

  /**
   * Check if PDF has changed based on mtime
   */
  isPdfChanged(data: StateUpdate): boolean {
    const newMtime = data.pdf_mtime ?? 0;
    return newMtime > this.state.pdfMtime;
  }

  /**
   * Set PDF loaded status
   */
  setPdfLoaded(loaded: boolean): void {
    this.state.pdfLoaded = loaded;
    this.notifyListeners();
  }

  /**
   * Set pending update
   */
  setPendingUpdate(update: StateUpdate | null): void {
    this.state.pendingUpdate = update;
    this.notifyListeners();
  }

  /**
   * Apply a full state update
   */
  applyUpdate(data: StateUpdate): void {
    this.state.page = data.page;
    this.state.y = data.y ?? null;
    
    const newSyncTime = data.last_sync_time ?? 0;
    if (newSyncTime > 0) {
      this.state.lastSyncTime = newSyncTime;
    }

    if (data.pdf_mtime !== undefined && data.pdf_mtime > 0) {
      this.state.pdfMtime = data.pdf_mtime;
    }

    if (data.pdf_loaded !== undefined) {
      this.state.pdfLoaded = data.pdf_loaded;
    }

    this.notifyListeners();
  }

  /**
   * Check if a state update has newer sync time than current
   */
  isNewerUpdate(data: StateUpdate): boolean {
    const newSyncTime = data.last_sync_time ?? 0;
    return newSyncTime > this.state.lastSyncTime;
  }

  /**
   * Reset state to initial values
   */
  reset(): void {
    this.state = {
      page: null,
      y: null,
      pdfMtime: 0,
      lastSyncTime: 0,
      pdfLoaded: false,
      pendingUpdate: null,
    };
    this.notifyListeners();
  }

  /**
   * Notify all listeners of state change
   */
  private notifyListeners(): void {
    const state = this.currentState;
    this.listeners.forEach(listener => {
      try {
        listener(state);
      } catch (e) {
        console.error('Error in state change listener:', e);
      }
    });
  }
}

/**
 * Create state manager with config
 */
export function createStateManager(config: PDFConfig): StateManager {
  return new StateManager({
    pdfLoaded: config.filename !== 'no-pdf-loaded',
    pdfMtime: config.mtime,
    lastSyncTime: config.mtime,
  });
}
