import { describe, it, expect } from 'vitest';
import { StateManager } from '../../../static/state-manager.js';

describe('StateManager in browser environment', () => {
  it('should create StateManager instance', () => {
    const stateManager = new StateManager({ pdfMtime: 1000 });
    expect(stateManager.pdfMtime).toBe(1000);
  });

  it('should update pdfMtime', () => {
    const stateManager = new StateManager({ pdfMtime: 1000 });
    stateManager.updatePdfMtime(2000);
    expect(stateManager.pdfMtime).toBe(2000);
  });

  it('should set and get pending update', () => {
    const stateManager = new StateManager({ pdfMtime: 1000 });
    
    stateManager.setPendingUpdate({
      page: 5,
      x: 100,
      y: 200,
      last_sync_time: 9999,
      action: 'synctex'
    });
    
    expect(stateManager.pendingUpdate).not.toBeNull();
    expect(stateManager.pendingUpdate?.page).toBe(5);
    expect(stateManager.pendingUpdate?.x).toBe(100);
    expect(stateManager.pendingUpdate?.y).toBe(200);
  });

  it('should reset state', () => {
    const stateManager = new StateManager({ 
      pdfMtime: 1000,
      page: 5,
      y: 200,
      pdfLoaded: true
    });
    
    stateManager.reset();
    
    expect(stateManager.pdfMtime).toBe(0);
    expect(stateManager.currentPage).toBeNull();
    expect(stateManager.currentY).toBeNull();
    expect(stateManager.isPdfLoaded).toBe(false);
    expect(stateManager.pendingUpdate).toBeNull();
  });

  it('should subscribe to state changes', () => {
    const stateManager = new StateManager({ pdfMtime: 1000 });
    let notified = false;
    
    stateManager.subscribe(() => {
      notified = true;
    });
    
    stateManager.updatePdfMtime(2000);
    expect(notified).toBe(true);
  });

  it('should check if PDF has changed', () => {
    const stateManager = new StateManager({ pdfMtime: 1000 });
    
    expect(stateManager.isPdfChanged({ page: 1, pdf_mtime: 2000 })).toBe(true);
    expect(stateManager.isPdfChanged({ page: 1, pdf_mtime: 500 })).toBe(false);
  });

  it('should check if sync is newer', () => {
    const stateManager = new StateManager({ lastSyncTime: 1000 });
    
    expect(stateManager.isNewerSync({ page: 1, last_sync_time: 2000 })).toBe(true);
    expect(stateManager.isNewerSync({ page: 1, last_sync_time: 500 })).toBe(false);
  });
});
