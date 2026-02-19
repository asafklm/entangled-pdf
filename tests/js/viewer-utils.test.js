import { describe, it, expect, beforeEach } from 'vitest';
import {
    getRenderScale,
    pdfYToPixels,
    calculateScrollPosition,
    createMarker,
    isValidStateUpdate,
    parseWebSocketMessage,
    calculateReconnectDelay,
    isNewerState,
    ACTION_SYNCTEX,
    MAX_RECONNECT_DELAY,
    MARKER_OFFSET,
    MARKER_DISPLAY_TIME
} from '../../static/viewer-utils.js';

describe('Constants', () => {
    it('should have correct action constant', () => {
        expect(ACTION_SYNCTEX).toBe('synctex');
    });

    it('should have correct max reconnect delay', () => {
        expect(MAX_RECONNECT_DELAY).toBe(30000);
    });

    it('should have correct marker offset', () => {
        expect(MARKER_OFFSET).toBe(5);
    });

    it('should have correct marker display time', () => {
        expect(MARKER_DISPLAY_TIME).toBe(5000);
    });
});

describe('getRenderScale', () => {
    it('should calculate correct scale for standard display', () => {
        const canvas = {
            style: { height: '800px' },
            height: 1600
        };
        global.window = { devicePixelRatio: 2 };
        
        const scale = getRenderScale(canvas);
        expect(scale).toBe(1); // (800 * 2) / 1600 = 1
    });

    it('should handle devicePixelRatio of 1', () => {
        const canvas = {
            style: { height: '600px' },
            height: 600
        };
        global.window = { devicePixelRatio: 1 };
        
        const scale = getRenderScale(canvas);
        expect(scale).toBe(1); // (600 * 1) / 600 = 1
    });

    it('should handle high DPI displays', () => {
        const canvas = {
            style: { height: '400px' },
            height: 1200
        };
        global.window = { devicePixelRatio: 3 };
        
        const scale = getRenderScale(canvas);
        expect(scale).toBe(1); // (400 * 3) / 1200 = 1
    });

    it('should default to devicePixelRatio of 1 when not defined', () => {
        const canvas = {
            style: { height: '500px' },
            height: 500
        };
        global.window = {};
        
        const scale = getRenderScale(canvas);
        expect(scale).toBe(1); // (500 * 1) / 500 = 1
    });
});

describe('pdfYToPixels', () => {
    it('should convert PDF y-coordinate to pixels', () => {
        const canvas = {
            style: { height: '800px' },
            height: 1600
        };
        global.window = { devicePixelRatio: 2 };
        
        const pixels = pdfYToPixels(canvas, 100);
        expect(pixels).toBe(100); // 100 * 1 = 100
    });

    it('should handle zero y-coordinate', () => {
        const canvas = {
            style: { height: '600px' },
            height: 600
        };
        global.window = { devicePixelRatio: 1 };
        
        const pixels = pdfYToPixels(canvas, 0);
        expect(pixels).toBe(0);
    });

    it('should handle large y-coordinates', () => {
        const canvas = {
            style: { height: '800px' },
            height: 1600
        };
        global.window = { devicePixelRatio: 2 };
        
        const pixels = pdfYToPixels(canvas, 1000);
        expect(pixels).toBe(1000);
    });
});

describe('calculateScrollPosition', () => {
    it('should calculate correct scroll position', () => {
        const container = {
            clientHeight: 800,
            style: {}
        };
        
        const target = {
            offsetTop: 200
        };
        
        const canvas = {
            style: { height: '600px' },
            height: 1200
        };
        
        global.window = {
            devicePixelRatio: 2,
            getComputedStyle: () => ({ paddingTop: '20px' })
        };
        
        const scrollPos = calculateScrollPosition(container, target, canvas, 300);
        // pixelY = 300 * 1 = 300
        // targetScrollTop = 200 + 300 - (800/2) + 20 = 200 + 300 - 400 + 20 = 120
        expect(scrollPos).toBe(120);
    });

    it('should not return negative scroll position', () => {
        const container = {
            clientHeight: 1000,
            style: {}
        };
        
        const target = {
            offsetTop: 0
        };
        
        const canvas = {
            style: { height: '600px' },
            height: 1200
        };
        
        global.window = {
            devicePixelRatio: 2,
            getComputedStyle: () => ({ paddingTop: '20px' })
        };
        
        const scrollPos = calculateScrollPosition(container, target, canvas, 10);
        // This would be negative, so it should return 0
        expect(scrollPos).toBe(0);
    });
});

describe('createMarker', () => {
    it('should create marker element with correct class', () => {
        const marker = createMarker(100);
        expect(marker.className).toBe('synctex-marker');
    });

    it('should position marker correctly with offset', () => {
        const marker = createMarker(100);
        expect(marker.style.top).toBe('95px'); // 100 - 5 = 95
    });

    it('should handle zero position', () => {
        const marker = createMarker(0);
        expect(marker.style.top).toBe('-5px'); // 0 - 5 = -5
    });
});

describe('isValidStateUpdate', () => {
    it('should return true for valid state update', () => {
        expect(isValidStateUpdate({ page: 5, y: 100 })).toBe(true);
    });

    it('should return true for valid state without y', () => {
        expect(isValidStateUpdate({ page: 3 })).toBe(true);
    });

    it('should return false for null', () => {
        expect(isValidStateUpdate(null)).toBeFalsy();
    });

    it('should return false for undefined', () => {
        expect(isValidStateUpdate(undefined)).toBeFalsy();
    });

    it('should return false for non-object', () => {
        expect(isValidStateUpdate('string')).toBe(false);
        expect(isValidStateUpdate(123)).toBe(false);
    });

    it('should return false for missing page', () => {
        expect(isValidStateUpdate({ y: 100 })).toBe(false);
    });

    it('should return false for non-numeric page', () => {
        expect(isValidStateUpdate({ page: 'five' })).toBe(false);
    });

    it('should return false for zero page', () => {
        expect(isValidStateUpdate({ page: 0 })).toBe(false);
    });

    it('should return false for negative page', () => {
        expect(isValidStateUpdate({ page: -1 })).toBe(false);
    });
});

describe('parseWebSocketMessage', () => {
    it('should parse valid JSON message', () => {
        const message = JSON.stringify({ action: 'synctex', page: 5 });
        const result = parseWebSocketMessage(message);
        expect(result).toEqual({ action: 'synctex', page: 5 });
    });

    it('should return null for invalid JSON', () => {
        const result = parseWebSocketMessage('not json');
        expect(result).toBeNull();
    });

    it('should return null for empty string', () => {
        const result = parseWebSocketMessage('');
        expect(result).toBeNull();
    });

    it('should parse complex nested objects', () => {
        const data = { action: 'synctex', page: 3, y: 150.5, timestamp: 1234567890 };
        const result = parseWebSocketMessage(JSON.stringify(data));
        expect(result).toEqual(data);
    });
});

describe('calculateReconnectDelay', () => {
    it('should calculate exponential backoff', () => {
        expect(calculateReconnectDelay(0)).toBe(1000); // 1000 * 2^0 = 1000
        expect(calculateReconnectDelay(1)).toBe(2000); // 1000 * 2^1 = 2000
        expect(calculateReconnectDelay(2)).toBe(4000); // 1000 * 2^2 = 4000
        expect(calculateReconnectDelay(3)).toBe(8000); // 1000 * 2^3 = 8000
    });

    it('should cap at MAX_RECONNECT_DELAY', () => {
        expect(calculateReconnectDelay(10)).toBe(MAX_RECONNECT_DELAY);
        expect(calculateReconnectDelay(20)).toBe(MAX_RECONNECT_DELAY);
    });

    it('should handle fractional attempts', () => {
        const delay = calculateReconnectDelay(1.5);
        expect(delay).toBeGreaterThan(2820);
        expect(delay).toBeLessThan(2835);
    });
});

describe('isNewerState', () => {
    it('should return true when new timestamp is greater', () => {
        const newData = { timestamp: 1000 };
        expect(isNewerState(newData, 500)).toBe(true);
    });

    it('should return false when new timestamp is equal', () => {
        const newData = { timestamp: 1000 };
        expect(isNewerState(newData, 1000)).toBe(false);
    });

    it('should return false when new timestamp is older', () => {
        const newData = { timestamp: 500 };
        expect(isNewerState(newData, 1000)).toBe(false);
    });

    it('should handle last_update_time field', () => {
        const newData = { last_update_time: 2000 };
        expect(isNewerState(newData, 1000)).toBe(true);
    });

    it('should prefer timestamp over last_update_time', () => {
        const newData = { timestamp: 3000, last_update_time: 1000 };
        expect(isNewerState(newData, 2000)).toBe(true);
    });

    it('should handle missing timestamps', () => {
        const newData = {};
        expect(isNewerState(newData, 0)).toBe(false);
        expect(isNewerState(newData, -1)).toBe(true);
    });
});
