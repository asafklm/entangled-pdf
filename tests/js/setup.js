/**
 * Test setup file for Vitest
 * Sets up DOM environment and global mocks
 */
import { vi } from 'vitest';
// Mock window.PDF_CONFIG using Object.assign to avoid type issues
Object.assign(global.window, {
    PDF_CONFIG: {
        port: 8431,
        filename: 'test.pdf'
    },
    devicePixelRatio: 1,
    getComputedStyle: () => ({ paddingTop: '20px' })
});
// Mock pdfjsLib on global using bracket notation to avoid type checking
// eslint-disable-next-line @typescript-eslint/no-explicit-any
global.pdfjsLib = {
    GlobalWorkerOptions: {
        workerSrc: ''
    },
    getDocument: vi.fn()
};
// Mock WebSocket
class MockWebSocket {
    constructor() {
        this.send = vi.fn();
        this.close = vi.fn();
        this.onopen = null;
        this.onmessage = null;
        this.onclose = null;
        this.onerror = null;
        this.readyState = 0;
        this.CONNECTING = 0;
        this.OPEN = 1;
        this.CLOSING = 2;
        this.CLOSED = 3;
    }
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
global.WebSocket = MockWebSocket;
// Mock fetch
global.fetch = vi.fn();
// Mock console methods to reduce noise in tests
global.console = {
    ...console,
    log: vi.fn(),
    error: vi.fn()
};
//# sourceMappingURL=setup.js.map