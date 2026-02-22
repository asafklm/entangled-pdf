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
  getComputedStyle: () => ({ paddingTop: '20px' }) as unknown as CSSStyleDeclaration
});

// Mock pdfjsLib on global using bracket notation to avoid type checking
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(global as any).pdfjsLib = {
  GlobalWorkerOptions: {
    workerSrc: ''
  },
  getDocument: vi.fn()
};

// Mock WebSocket
class MockWebSocket {
  send = vi.fn();
  close = vi.fn();
  onopen: ((this: WebSocket, ev: Event) => unknown) | null = null;
  onmessage: ((this: WebSocket, ev: MessageEvent) => unknown) | null = null;
  onclose: ((this: WebSocket, ev: CloseEvent) => unknown) | null = null;
  onerror: ((this: WebSocket, ev: Event) => unknown) | null = null;
  readyState: number = 0;
  CONNECTING: number = 0;
  OPEN: number = 1;
  CLOSING: number = 2;
  CLOSED: number = 3;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
(global as any).WebSocket = MockWebSocket;

// Mock fetch
global.fetch = vi.fn();

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  log: vi.fn(),
  error: vi.fn()
} as Console;
