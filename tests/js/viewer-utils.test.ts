import { describe, it, expect, beforeEach } from 'vitest';
import type { MockCanvas, StateUpdate, WebSocketData } from '../../static/viewer-utils';
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
} from '../../static/viewer-utils';

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
    const canvas: MockCanvas = {
      style: { height: '800px' },
      height: 1600
    };
    global.window = { ...global.window, devicePixelRatio: 2 } as unknown as Window & typeof globalThis;

    const scale: number = getRenderScale(canvas);
    expect(scale).toBe(1); // (800 * 2) / 1600 = 1
  });

  it('should handle devicePixelRatio of 1', () => {
    const canvas: MockCanvas = {
      style: { height: '600px' },
      height: 600
    };
    global.window = { ...global.window, devicePixelRatio: 1 } as unknown as Window & typeof globalThis;

    const scale: number = getRenderScale(canvas);
    expect(scale).toBe(1); // (600 * 1) / 600 = 1
  });

  it('should handle high DPI displays', () => {
    const canvas: MockCanvas = {
      style: { height: '400px' },
      height: 1200
    };
    global.window = { ...global.window, devicePixelRatio: 3 } as unknown as Window & typeof globalThis;

    const scale: number = getRenderScale(canvas);
    expect(scale).toBe(1); // (400 * 3) / 1200 = 1
  });

  it('should default to devicePixelRatio of 1 when not defined', () => {
    const canvas: MockCanvas = {
      style: { height: '500px' },
      height: 500
    };
    global.window = { ...global.window, devicePixelRatio: undefined } as unknown as Window & typeof globalThis;

    const scale: number = getRenderScale(canvas);
    expect(scale).toBe(1); // (500 * 1) / 500 = 1
  });
});

describe('pdfYToPixels', () => {
  it('should convert PDF y-coordinate to pixels with default scale 1.0', () => {
    const canvas: MockCanvas = {
      style: { height: '800px' },
      height: 1600
    };
    global.window = { ...global.window, devicePixelRatio: 2 } as unknown as Window & typeof globalThis;

    const pixels: number = pdfYToPixels(canvas, 100);
    expect(pixels).toBe(100); // 100 * 1.0 * 1 = 100
  });

  it('should convert PDF y-coordinate to pixels with scale 1.5', () => {
    const canvas: MockCanvas = {
      style: { height: '800px' },
      height: 1600
    };
    global.window = { ...global.window, devicePixelRatio: 2 } as unknown as Window & typeof globalThis;

    const pixels: number = pdfYToPixels(canvas, 100, 1.5);
    expect(pixels).toBe(150); // 100 * 1.5 * 1 = 150
  });

  it('should convert PDF y-coordinate to pixels with scale 2.0', () => {
    const canvas: MockCanvas = {
      style: { height: '800px' },
      height: 1600
    };
    global.window = { ...global.window, devicePixelRatio: 2 } as unknown as Window & typeof globalThis;

    const pixels: number = pdfYToPixels(canvas, 100, 2.0);
    expect(pixels).toBe(200); // 100 * 2.0 * 1 = 200
  });

  it('should handle zero y-coordinate', () => {
    const canvas: MockCanvas = {
      style: { height: '600px' },
      height: 600
    };
    global.window = { ...global.window, devicePixelRatio: 1 } as unknown as Window & typeof globalThis;

    const pixels: number = pdfYToPixels(canvas, 0, 1.0);
    expect(pixels).toBe(0);
  });

  it('should handle y at top of page (small y value)', () => {
    const canvas: MockCanvas = {
      style: { height: '600px' },
      height: 600
    };
    global.window = { ...global.window, devicePixelRatio: 1 } as unknown as Window & typeof globalThis;

    const yFromTop = 50; // Near top of page
    const pixels: number = pdfYToPixels(canvas, yFromTop, 1.0);
    expect(pixels).toBe(50); // 50 * 1.0 = 50 (near top)
  });

  it('should handle y at bottom of page (large y value)', () => {
    const canvas: MockCanvas = {
      style: { height: '600px' },
      height: 600
    };
    global.window = { ...global.window, devicePixelRatio: 1 } as unknown as Window & typeof globalThis;

    const yFromTop = 550; // Near bottom of page
    const pixels: number = pdfYToPixels(canvas, yFromTop, 1.0);
    expect(pixels).toBe(550); // 550 * 1.0 = 550 (near bottom)
  });

  it('should handle large y-coordinates with scale', () => {
    const canvas: MockCanvas = {
      style: { height: '800px' },
      height: 1600
    };
    global.window = { ...global.window, devicePixelRatio: 2 } as unknown as Window & typeof globalThis;

    const pixels: number = pdfYToPixels(canvas, 500, 1.5);
    expect(pixels).toBe(750); // 500 * 1.5 * 1 = 750
  });
});

describe('calculateScrollPosition', () => {
  it('should calculate correct scroll position with default scale', () => {
    const container: HTMLElement = {
      clientHeight: 800,
      style: {}
    } as HTMLElement;

    const target: { offsetTop: number } = {
      offsetTop: 200
    };

    const canvas: MockCanvas = {
      style: { height: '600px' },
      height: 1200
    };

    global.window = {
      ...global.window,
      devicePixelRatio: 2,
      getComputedStyle: () => ({ paddingTop: '20px' } as CSSStyleDeclaration)
    } as unknown as Window & typeof globalThis;

    const scrollPos: number = calculateScrollPosition(container, target, canvas, 300);
    // pixelY = 300 * 1.0 * 1 = 300
    // targetScrollTop = 200 + 300 - (800/2) + 20 = 200 + 300 - 400 + 20 = 120
    expect(scrollPos).toBe(120);
  });

  it('should calculate correct scroll position with scale 1.5', () => {
    const container: HTMLElement = {
      clientHeight: 800,
      style: {}
    } as HTMLElement;

    const target: { offsetTop: number } = {
      offsetTop: 200
    };

    const canvas: MockCanvas = {
      style: { height: '600px' },
      height: 1200
    };

    global.window = {
      ...global.window,
      devicePixelRatio: 2,
      getComputedStyle: () => ({ paddingTop: '20px' } as CSSStyleDeclaration)
    } as unknown as Window & typeof globalThis;

    const scrollPos: number = calculateScrollPosition(container, target, canvas, 300, 1.5);
    // pixelY = 300 * 1.5 * 1 = 450
    // targetScrollTop = 200 + 450 - (800/2) + 20 = 200 + 450 - 400 + 20 = 270
    expect(scrollPos).toBe(270);
  });

  it('should calculate correct scroll position with scale 2.0', () => {
    const container: HTMLElement = {
      clientHeight: 800,
      style: {}
    } as HTMLElement;

    const target: { offsetTop: number } = {
      offsetTop: 200
    };

    const canvas: MockCanvas = {
      style: { height: '600px' },
      height: 1200
    };

    global.window = {
      ...global.window,
      devicePixelRatio: 2,
      getComputedStyle: () => ({ paddingTop: '20px' } as CSSStyleDeclaration)
    } as unknown as Window & typeof globalThis;

    const scrollPos: number = calculateScrollPosition(container, target, canvas, 200, 2.0);
    // pixelY = 200 * 2.0 * 1 = 400
    // targetScrollTop = 200 + 400 - (800/2) + 20 = 200 + 400 - 400 + 20 = 220
    expect(scrollPos).toBe(220);
  });

  it('should not return negative scroll position', () => {
    const container: HTMLElement = {
      clientHeight: 1000,
      style: {}
    } as HTMLElement;

    const target: { offsetTop: number } = {
      offsetTop: 0
    };

    const canvas: MockCanvas = {
      style: { height: '600px' },
      height: 1200
    };

    global.window = {
      ...global.window,
      devicePixelRatio: 2,
      getComputedStyle: () => ({ paddingTop: '20px' } as CSSStyleDeclaration)
    } as unknown as Window & typeof globalThis;

    const scrollPos: number = calculateScrollPosition(container, target, canvas, 10, 1.0);
    // pixelY = 10 * 1.0 * 1 = 10
    // targetScrollTop = 0 + 10 - (1000/2) + 20 = 10 - 500 + 20 = -470 -> 0
    expect(scrollPos).toBe(0);
  });

  it('should handle y near top of page correctly', () => {
    const container: HTMLElement = {
      clientHeight: 800,
      style: {}
    } as HTMLElement;

    const target: { offsetTop: number } = {
      offsetTop: 100
    };

    const canvas: MockCanvas = {
      style: { height: '792px' },
      height: 1584
    };

    global.window = {
      ...global.window,
      devicePixelRatio: 2,
      getComputedStyle: () => ({ paddingTop: '20px' } as CSSStyleDeclaration)
    } as unknown as Window & typeof globalThis;

    // SynTeX Y for line 5 (title near top): ~159 pts
    const synctexY = 159;
    const pdfScale = 1.5;
    const scrollPos: number = calculateScrollPosition(container, target, canvas, synctexY, pdfScale);
    // pixelY = 159 * 1.5 * 1 = 238.5
    // targetScrollTop = 100 + 238.5 - (800/2) + 20 = 100 + 238.5 - 400 + 20 = -41.5 -> 0
    expect(scrollPos).toBe(0);
  });

  it('should handle y near bottom of page correctly', () => {
    const container: HTMLElement = {
      clientHeight: 800,
      style: {}
    } as HTMLElement;

    const target: { offsetTop: number } = {
      offsetTop: 100
    };

    const canvas: MockCanvas = {
      style: { height: '792px' },
      height: 1584
    };

    global.window = {
      ...global.window,
      devicePixelRatio: 2,
      getComputedStyle: () => ({ paddingTop: '20px' } as CSSStyleDeclaration)
    } as unknown as Window & typeof globalThis;

    // SynTeX Y for line 44 (near bottom of page 1): ~628 pts
    const synctexY = 628;
    const pdfScale = 1.5;
    const scrollPos: number = calculateScrollPosition(container, target, canvas, synctexY, pdfScale);
    // pixelY = 628 * 1.5 * 1 = 942
    // targetScrollTop = 100 + 942 - (800/2) + 20 = 100 + 942 - 400 + 20 = 662
    expect(scrollPos).toBe(662);
  });
});

describe('createMarker', () => {
  it('should create marker element with correct class', () => {
    const marker: HTMLElement = createMarker(100);
    expect(marker.className).toBe('synctex-marker');
  });

  it('should position marker correctly with offset', () => {
    const marker: HTMLElement = createMarker(100);
    expect(marker.style.top).toBe('95px'); // 100 - 5 = 95
  });

  it('should handle zero position', () => {
    const marker: HTMLElement = createMarker(0);
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
    const message: string = JSON.stringify({ action: 'synctex', page: 5 });
    const result: WebSocketData | null = parseWebSocketMessage(message);
    expect(result).toEqual({ action: 'synctex', page: 5 });
  });

  it('should return null for invalid JSON', () => {
    const result: WebSocketData | null = parseWebSocketMessage('not json');
    expect(result).toBeNull();
  });

  it('should return null for empty string', () => {
    const result: WebSocketData | null = parseWebSocketMessage('');
    expect(result).toBeNull();
  });

  it('should parse complex nested objects', () => {
    const data: WebSocketData = { action: 'synctex', page: 3, y: 150.5, timestamp: 1234567890 };
    const result: WebSocketData | null = parseWebSocketMessage(JSON.stringify(data));
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
    const delay: number = calculateReconnectDelay(1.5);
    expect(delay).toBeGreaterThan(2820);
    expect(delay).toBeLessThan(2835);
  });
});

describe('isNewerState', () => {
  it('should return true when new timestamp is greater', () => {
    const newData: StateUpdate = { timestamp: 1000 };
    expect(isNewerState(newData, 500)).toBe(true);
  });

  it('should return false when new timestamp is equal', () => {
    const newData: StateUpdate = { timestamp: 1000 };
    expect(isNewerState(newData, 1000)).toBe(false);
  });

  it('should return false when new timestamp is older', () => {
    const newData: StateUpdate = { timestamp: 500 };
    expect(isNewerState(newData, 1000)).toBe(false);
  });

  it('should handle last_update_time field', () => {
    const newData: StateUpdate = { last_update_time: 2000 };
    expect(isNewerState(newData, 1000)).toBe(true);
  });

  it('should prefer timestamp over last_update_time', () => {
    const newData: StateUpdate = { timestamp: 3000, last_update_time: 1000 };
    expect(isNewerState(newData, 2000)).toBe(true);
  });

  it('should handle missing timestamps', () => {
    const newData: StateUpdate = {};
    expect(isNewerState(newData, 0)).toBe(false);
    expect(isNewerState(newData, -1)).toBe(true);
  });
});
