import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  clearAllMarkers,
  createMarker,
  showMarker,
  showMarkerAtPdfCoordinates,
  showMarkerAtPage,
} from '../../static/marker-manager';
import { MARKER_DISPLAY_TIME, MARKER_OFFSET } from '../../static/constants';
import * as coordinateUtils from '../../static/coordinate-utils';

describe('Marker Manager', () => {
  beforeEach(() => {
    // Clean up document body
    document.body.innerHTML = '';
    vi.useFakeTimers();
  });

  afterEach(() => {
    // Clean up any remaining markers
    clearAllMarkers();
    vi.runAllTimers();
    vi.useRealTimers();
    vi.clearAllTimers();
    document.body.innerHTML = '';
  });

  describe('clearAllMarkers()', () => {
    it('should remove all markers from the document', () => {
      // Create multiple markers
      const marker1 = createMarker(100);
      const marker2 = createMarker(200);
      const marker3 = createMarker(300);
      
      document.body.appendChild(marker1);
      document.body.appendChild(marker2);
      document.body.appendChild(marker3);
      
      expect(document.querySelectorAll('.synctex-marker').length).toBe(3);
      
      clearAllMarkers();
      
      expect(document.querySelectorAll('.synctex-marker').length).toBe(0);
    });

    it('should handle no markers gracefully', () => {
      expect(document.querySelectorAll('.synctex-marker').length).toBe(0);
      
      // Should not throw
      expect(() => clearAllMarkers()).not.toThrow();
      
      expect(document.querySelectorAll('.synctex-marker').length).toBe(0);
    });

    it('should only remove synctex-markers, not other elements', () => {
      const marker = createMarker(100);
      const otherDiv = document.createElement('div');
      otherDiv.className = 'other-element';
      
      document.body.appendChild(marker);
      document.body.appendChild(otherDiv);
      
      clearAllMarkers();
      
      expect(document.querySelector('.synctex-marker')).toBeNull();
      expect(document.querySelector('.other-element')).not.toBeNull();
    });
  });

  describe('createMarker()', () => {
    it('should create a marker element with correct class', () => {
      const marker = createMarker(150);
      
      expect(marker.className).toBe('synctex-marker');
      expect(marker.tagName).toBe('DIV');
    });

    it('should set vertical position with MARKER_OFFSET adjustment', () => {
      const pixelY = 200;
      const marker = createMarker(pixelY);
      
      const expectedTop = pixelY - MARKER_OFFSET;
      expect(marker.style.top).toBe(`${expectedTop}px`);
    });

    it('should set absolute positioning', () => {
      const marker = createMarker(100);
      
      expect(marker.style.position).toBe('absolute');
    });

    it('should not set horizontal position when pixelX is not provided', () => {
      const marker = createMarker(100);
      
      // Should rely on CSS class default (left: 5px)
      expect(marker.style.left).toBe('');
    });

    it('should set horizontal position with MARKER_OFFSET adjustment when pixelX provided', () => {
      const pixelX = 300;
      const marker = createMarker(100, pixelX);
      
      const expectedLeft = pixelX - MARKER_OFFSET;
      expect(marker.style.left).toBe(`${expectedLeft}px`);
    });

    it('should handle pixelX of 0 correctly', () => {
      const marker = createMarker(100, 0);
      
      const expectedLeft = 0 - MARKER_OFFSET;
      expect(marker.style.left).toBe(`${expectedLeft}px`);
    });

    it('should handle coordinates at boundaries', () => {
      const marker = createMarker(0, 0);
      
      expect(marker.style.top).toBe(`${-MARKER_OFFSET}px`);
      expect(marker.style.left).toBe(`${-MARKER_OFFSET}px`);
    });

    it('should handle very large coordinates', () => {
      const largeY = 10000;
      const largeX = 5000;
      
      const marker = createMarker(largeY, largeX);
      
      expect(marker.style.top).toBe(`${largeY - MARKER_OFFSET}px`);
      expect(marker.style.left).toBe(`${largeX - MARKER_OFFSET}px`);
    });
  });

  describe('showMarker()', () => {
    it('should create and append marker to page wrapper', () => {
      const pageWrapper = document.createElement('div');
      document.body.appendChild(pageWrapper);
      
      showMarker(pageWrapper, 150);
      
      const marker = pageWrapper.querySelector('.synctex-marker');
      expect(marker).not.toBeNull();
      expect(pageWrapper.contains(marker)).toBe(true);
    });

    it('should set page wrapper to relative positioning', () => {
      const pageWrapper = document.createElement('div');
      document.body.appendChild(pageWrapper);
      
      showMarker(pageWrapper, 150);
      
      expect(pageWrapper.style.position).toBe('relative');
    });

    it('should clear existing markers before showing new one', () => {
      const pageWrapper = document.createElement('div');
      document.body.appendChild(pageWrapper);
      
      // Create first marker
      showMarker(pageWrapper, 100);
      expect(pageWrapper.querySelectorAll('.synctex-marker').length).toBe(1);
      
      // Create second marker - should replace first
      showMarker(pageWrapper, 200);
      const markers = pageWrapper.querySelectorAll('.synctex-marker');
      expect(markers.length).toBe(1);
      
      // Verify it's the new marker
      expect((markers[0] as HTMLElement).style.top).toBe(`${200 - MARKER_OFFSET}px`);
    });

    it('should auto-remove marker after default display time', () => {
      const pageWrapper = document.createElement('div');
      document.body.appendChild(pageWrapper);
      
      showMarker(pageWrapper, 150);
      
      expect(pageWrapper.querySelector('.synctex-marker')).not.toBeNull();
      
      // Fast forward past display time
      vi.advanceTimersByTime(MARKER_DISPLAY_TIME);
      
      expect(pageWrapper.querySelector('.synctex-marker')).toBeNull();
    });

    it('should auto-remove marker after custom display time', () => {
      const pageWrapper = document.createElement('div');
      document.body.appendChild(pageWrapper);
      
      const customTime = 1000;
      showMarker(pageWrapper, 150, undefined, customTime);
      
      // Should still be visible before custom time
      vi.advanceTimersByTime(customTime - 100);
      expect(pageWrapper.querySelector('.synctex-marker')).not.toBeNull();
      
      // Should be removed after custom time
      vi.advanceTimersByTime(100);
      expect(pageWrapper.querySelector('.synctex-marker')).toBeNull();
    });

    it('should show marker at specific X position when provided', () => {
      const pageWrapper = document.createElement('div');
      document.body.appendChild(pageWrapper);
      
      showMarker(pageWrapper, 150, 300);
      
      const marker = pageWrapper.querySelector('.synctex-marker') as HTMLElement;
      expect(marker.style.left).toBe(`${300 - MARKER_OFFSET}px`);
    });

    it('should handle multiple showMarker calls with different wrappers', () => {
      const wrapper1 = document.createElement('div');
      const wrapper2 = document.createElement('div');
      document.body.appendChild(wrapper1);
      document.body.appendChild(wrapper2);
      
      showMarker(wrapper1, 100);
      
      // Should clear marker from wrapper1 when showing on wrapper2
      showMarker(wrapper2, 200);
      
      // wrapper1 should have no markers (cleared)
      expect(wrapper1.querySelector('.synctex-marker')).toBeNull();
      
      // wrapper2 should have the marker
      expect(wrapper2.querySelector('.synctex-marker')).not.toBeNull();
    });
  });

  describe('showMarkerAtPdfCoordinates()', () => {
    it('should convert PDF coordinates to pixel coordinates and show marker', () => {
      const pageWrapper = document.createElement('div');
      document.body.appendChild(pageWrapper);
      
      // Mock canvas
      const mockCanvas = {
        style: { height: '800px' },
        height: 800,
      } as any;
      
      // Mock coordinate conversion
      const mockPixelY = 200;
      vi.spyOn(coordinateUtils, 'pdfYToPixels').mockReturnValue(mockPixelY);
      
      showMarkerAtPdfCoordinates(pageWrapper, mockCanvas, 1.5, 500);
      
      const marker = pageWrapper.querySelector('.synctex-marker') as HTMLElement;
      expect(marker).not.toBeNull();
      expect(marker.style.top).toBe(`${mockPixelY - MARKER_OFFSET}px`);
      
      // Should not have set left (no X coordinate provided)
      expect(marker.style.left).toBe('');
    });

    it('should handle both X and Y PDF coordinates', () => {
      const pageWrapper = document.createElement('div');
      document.body.appendChild(pageWrapper);
      
      const mockCanvas = {
        style: { height: '800px' },
        height: 800,
      } as any;
      
      const mockPixelY = 200;
      const mockPixelX = 300;
      
      vi.spyOn(coordinateUtils, 'pdfToPixelPosition').mockReturnValue({
        pixelX: mockPixelX,
        pixelY: mockPixelY,
      });
      
      showMarkerAtPdfCoordinates(pageWrapper, mockCanvas, 1.5, 500, 400);
      
      const marker = pageWrapper.querySelector('.synctex-marker') as HTMLElement;
      expect(marker.style.top).toBe(`${mockPixelY - MARKER_OFFSET}px`);
      expect(marker.style.left).toBe(`${mockPixelX - MARKER_OFFSET}px`);
    });

    it('should return early when Y is null', () => {
      const pageWrapper = document.createElement('div');
      document.body.appendChild(pageWrapper);
      
      const mockCanvas = {} as any;
      
      showMarkerAtPdfCoordinates(pageWrapper, mockCanvas, 1.5, null as any);
      
      expect(pageWrapper.querySelector('.synctex-marker')).toBeNull();
    });

    it('should use provided display time', () => {
      const pageWrapper = document.createElement('div');
      document.body.appendChild(pageWrapper);
      
      const mockCanvas = {
        style: { height: '800px' },
        height: 800,
      } as any;
      
      vi.spyOn(coordinateUtils, 'pdfYToPixels').mockReturnValue(200);
      
      const customTime = 500;
      showMarkerAtPdfCoordinates(pageWrapper, mockCanvas, 1.5, 500, undefined, customTime);
      
      vi.advanceTimersByTime(customTime - 100);
      expect(pageWrapper.querySelector('.synctex-marker')).not.toBeNull();
      
      vi.advanceTimersByTime(100);
      expect(pageWrapper.querySelector('.synctex-marker')).toBeNull();
    });
  });

  describe('showMarkerAtPage()', () => {
    it('should show marker at specific page by number', () => {
      const page1 = document.createElement('div');
      page1.className = 'page-wrapper';
      const canvas1 = document.createElement('canvas');
      page1.appendChild(canvas1);
      document.body.appendChild(page1);
      
      const pageElements: { [key: number]: HTMLElement } = {
        1: page1,
      };
      const pageScales: { [key: number]: number } = {
        1: 1.5,
      };
      
      // Mock coordinate conversion
      vi.spyOn(coordinateUtils, 'pdfYToPixels').mockReturnValue(200);
      
      showMarkerAtPage(pageElements, pageScales, 1, 500);
      
      const marker = page1.querySelector('.synctex-marker');
      expect(marker).not.toBeNull();
    });

    it('should return early when page does not exist', () => {
      const pageElements: { [key: number]: HTMLElement } = {};
      const pageScales: { [key: number]: number } = {};
      
      // Should not throw
      expect(() => {
        showMarkerAtPage(pageElements, pageScales, 1, 500);
      }).not.toThrow();
    });

    it('should return early when page has no canvas', () => {
      const page1 = document.createElement('div');
      page1.className = 'page-wrapper';
      // No canvas appended
      document.body.appendChild(page1);
      
      const pageElements: { [key: number]: HTMLElement } = {
        1: page1,
      };
      const pageScales: { [key: number]: number } = {
        1: 1.5,
      };
      
      // Should not throw
      expect(() => {
        showMarkerAtPage(pageElements, pageScales, 1, 500);
      }).not.toThrow();
      
      expect(page1.querySelector('.synctex-marker')).toBeNull();
    });

    it('should use default scale of 1.0 when not in pageScales', () => {
      const page1 = document.createElement('div');
      page1.className = 'page-wrapper';
      const canvas1 = document.createElement('canvas');
      canvas1.style.height = '800px';
      page1.appendChild(canvas1);
      document.body.appendChild(page1);
      
      const pageElements: { [key: number]: HTMLElement } = {
        1: page1,
      };
      const pageScales: { [key: number]: number } = {}; // Empty, should use 1.0
      
      const pdfYToPixelsSpy = vi.spyOn(coordinateUtils, 'pdfYToPixels').mockReturnValue(200);
      
      showMarkerAtPage(pageElements, pageScales, 1, 500);
      
      // Should have been called with scale 1.0 (default)
      expect(pdfYToPixelsSpy).toHaveBeenCalledWith(expect.anything(), 500, 1.0);
    });

    it('should handle X coordinate when provided', () => {
      const page1 = document.createElement('div');
      page1.className = 'page-wrapper';
      const canvas1 = document.createElement('canvas');
      canvas1.style.height = '800px';
      page1.appendChild(canvas1);
      document.body.appendChild(page1);
      
      const pageElements: { [key: number]: HTMLElement } = {
        1: page1,
      };
      const pageScales: { [key: number]: number } = {
        1: 1.5,
      };
      
      vi.spyOn(coordinateUtils, 'pdfToPixelPosition').mockReturnValue({
        pixelX: 300,
        pixelY: 200,
      });
      
      showMarkerAtPage(pageElements, pageScales, 1, 500, 400);
      
      const marker = page1.querySelector('.synctex-marker') as HTMLElement;
      expect(marker.style.left).toBe(`${300 - MARKER_OFFSET}px`);
    });

    it('should clear existing markers when showing on different page', () => {
      const page1 = document.createElement('div');
      const page2 = document.createElement('div');
      
      const canvas1 = document.createElement('canvas');
      const canvas2 = document.createElement('canvas');
      
      page1.appendChild(canvas1);
      page2.appendChild(canvas2);
      
      document.body.appendChild(page1);
      document.body.appendChild(page2);
      
      const pageElements: { [key: number]: HTMLElement } = {
        1: page1,
        2: page2,
      };
      const pageScales: { [key: number]: number } = {
        1: 1.0,
        2: 1.0,
      };
      
      vi.spyOn(coordinateUtils, 'pdfYToPixels').mockReturnValue(200);
      
      // Show on page 1
      showMarkerAtPage(pageElements, pageScales, 1, 500);
      expect(page1.querySelector('.synctex-marker')).not.toBeNull();
      
      // Show on page 2 - should clear page 1's marker
      showMarkerAtPage(pageElements, pageScales, 2, 600);
      expect(page1.querySelector('.synctex-marker')).toBeNull();
      expect(page2.querySelector('.synctex-marker')).not.toBeNull();
    });
  });

  describe('Integration scenarios', () => {
    it('should handle rapid successive marker shows', () => {
      const pageWrapper = document.createElement('div');
      document.body.appendChild(pageWrapper);
      
      // Show multiple markers rapidly
      for (let i = 0; i < 5; i++) {
        showMarker(pageWrapper, 100 + i * 50);
      }
      
      // Only one marker should exist
      expect(pageWrapper.querySelectorAll('.synctex-marker').length).toBe(1);
    });

    it('should handle markers across page reload simulation', () => {
      const pageWrapper = document.createElement('div');
      document.body.appendChild(pageWrapper);
      
      // Show marker
      showMarker(pageWrapper, 200, 300, 5000);
      expect(pageWrapper.querySelector('.synctex-marker')).not.toBeNull();
      
      // Simulate "page reload" by clearing body
      document.body.innerHTML = '';
      
      // Marker should be gone
      expect(document.querySelector('.synctex-marker')).toBeNull();
      
      // Can create new wrapper and show new marker
      const newWrapper = document.createElement('div');
      document.body.appendChild(newWrapper);
      showMarker(newWrapper, 150);
      expect(newWrapper.querySelector('.synctex-marker')).not.toBeNull();
    });

    it('should maintain correct positioning with different scales', () => {
      const pageWrapper = document.createElement('div');
      document.body.appendChild(pageWrapper);
      
      const mockCanvas = {
        style: { height: '800px' },
        height: 800,
      } as any;
      
      const scales = [0.5, 1.0, 1.5, 2.0];
      
      scales.forEach((scale, index) => {
        const expectedY = 100 + index * 50;
        vi.spyOn(coordinateUtils, 'pdfYToPixels').mockReturnValue(expectedY);
        
        showMarkerAtPdfCoordinates(pageWrapper, mockCanvas, scale, 500);
        
        const marker = pageWrapper.querySelector('.synctex-marker') as HTMLElement;
        expect(marker.style.top).toBe(`${expectedY - MARKER_OFFSET}px`);
        
        // Clear for next iteration
        clearAllMarkers();
      });
    });
  });
});
