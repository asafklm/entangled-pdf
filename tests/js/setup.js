/**
 * Test setup file for Vitest
 * Sets up DOM environment and global mocks
 */

import { vi } from 'vitest';

// Mock window.PDF_CONFIG
global.window = {
  ...global.window,
  PDF_CONFIG: {
    port: 8431,
    filename: 'test.pdf'
  }
};

// Mock pdfjsLib
global.pdfjsLib = {
  GlobalWorkerOptions: {
    workerSrc: ''
  },
  getDocument: vi.fn()
};

// Mock WebSocket
global.WebSocket = vi.fn().mockImplementation(() => ({
  send: vi.fn(),
  close: vi.fn(),
  onopen: null,
  onmessage: null,
  onclose: null,
  onerror: null
}));

// Mock fetch
global.fetch = vi.fn();

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  log: vi.fn(),
  error: vi.fn()
};
