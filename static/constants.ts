/**
 * EntangledPdf Viewer - Constants
 *
 * Centralized constants for the PDF viewer.
 */

// Action constants
export const ACTION_SYNCTEX = 'synctex' as const;
export const ACTION_RELOAD = 'reload' as const;
export const ACTION_INVERSE_SEARCH = 'inverse_search' as const;

// Marker constants
export const MARKER_DISPLAY_TIME = 5000;
export const MARKER_OFFSET = 5; // Center the 10px dot
export const MARKER_SIZE = 10;

// Keyboard constants
export const KEY_TIMEOUT_MS = 500;
export const LINE_SCROLL_AMOUNT = 40;
export const HORIZONTAL_SCROLL_AMOUNT = 40;

// Long press constants
export const LONG_PRESS_DURATION_MS = 500;
export const LONG_PRESS_MOVE_THRESHOLD = 10; // pixels

// Scroll constants
export const MAX_SCROLL_ATTEMPTS = 10;
export const SCROLL_RETRY_DELAY = 100;
export const SCROLL_VERIFY_DELAY = 50;
export const SCROLL_THRESHOLD = 5; // pixels

// WebSocket constants
export const WEBSOCKET_CHECK_INTERVAL = 100;
export const WEBSOCKET_CONNECT_TIMEOUT = 3000;
export const RECONNECT_DELAY_BASE = 1000;
export const MAX_RECONNECT_DELAY = 30000;
export const POLLING_INTERVAL = 2000;
export const WEBSOCKET_PING_INTERVAL = 25000; // 25 seconds - before server's 30s timeout

// Tooltip constants
export const TOOLTIP_AUTO_HIDE_DELAY = 3000;
export const FEEDBACK_DISPLAY_TIME = 1000;
export const MARKER_DELAY_AFTER_RELOAD = 150;

// Page navigation
export const PAGE_SCROLL_PERCENTAGE = 0.9;
export const UPPER_VIEWPORT_PERCENTAGE = 0.25;
export const MIN_UPPER_OFFSET_PX = 100;

// Default values
export const DEFAULT_PORT = 8431;
export const DEFAULT_FILENAME = 'document.pdf';
