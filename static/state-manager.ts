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
      timestamp: initialState?.timestamp ?? 0,
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
   * Get last update timestamp
   */
  get lastTimestamp(): number {
    return this.state.timestamp;
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
   * Update position and timestamp
   */
  updatePosition(page: number, y?: number, timestamp?: number): void {
    this.state.page = page;
    this.state.y = y ?? null;
    if (timestamp !== undefined) {
      this.state.timestamp = timestamp;
    }
    this.notifyListeners();
  }

  /**
   * Update timestamp from state update
   */
  updateTimestamp(data: StateUpdate): void {
    const newTimestamp = data.timestamp ?? data.last_update_time ?? 0;
    if (newTimestamp > this.state.timestamp) {
      this.state.timestamp = newTimestamp;
      this.notifyListeners();
    }
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
    
    const newTimestamp = data.timestamp ?? data.last_update_time ?? 0;
    if (newTimestamp > 0) {
      this.state.timestamp = newTimestamp;
    }

    if (data.pdf_loaded !== undefined) {
      this.state.pdfLoaded = data.pdf_loaded;
    }

    this.notifyListeners();
  }

  /**
   * Check if a state update is newer than current
   */
  isNewerUpdate(data: StateUpdate): boolean {
    const newTimestamp = data.timestamp ?? data.last_update_time ?? 0;
    return newTimestamp > this.state.timestamp;
  }

  /**
   * Reset state to initial values
   */
  reset(): void {
    this.state = {
      page: null,
      y: null,
      timestamp: 0,
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
    timestamp: config.mtime,
  });
}
