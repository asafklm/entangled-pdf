/**
 * PdfServer Viewer - Testable Module
 *
 * Extracted functions from viewer.js for unit testing
 */
export declare const ACTION_SYNCTEX: string;
export declare const MAX_RECONNECT_DELAY: number;
export declare const POLLING_INTERVAL: number;
export declare const MARKER_DISPLAY_TIME: number;
export declare const MARKER_OFFSET: number;
/**
 * Mock canvas interface for testing
 */
export interface MockCanvas {
    style: {
        height: string;
    };
    height: number;
}
/**
 * State update data structure
 */
export interface StateUpdate {
    page: number;
    y?: number;
    timestamp?: number;
    last_update_time?: number;
}
/**
 * WebSocket message data structure
 */
export interface WebSocketData {
    action?: string;
    page?: number;
    y?: number;
    timestamp?: number;
    last_update_time?: number;
}
/**
 * Calculate render scale from canvas dimensions
 * @param canvas - The canvas element (or mock for testing)
 * @returns Render scale factor
 */
export declare function getRenderScale(canvas: MockCanvas): number;
/**
 * Convert PDF y-coordinate to CSS pixels
 * @param canvas - The canvas element
 * @param y - Y coordinate in PDF points
 * @returns Pixel Y coordinate
 */
export declare function pdfYToPixels(canvas: MockCanvas, y: number): number;
/**
 * Calculate scroll position for a given page and y-coordinate
 * @param container - The scroll container
 * @param target - The target page element
 * @param canvas - The canvas element
 * @param y - Y coordinate in PDF points
 * @returns The scroll top position
 */
export declare function calculateScrollPosition(container: HTMLElement, target: {
    offsetTop: number;
}, canvas: MockCanvas, y: number): number;
/**
 * Create a marker element at the specified position
 * @param pixelY - Y position in pixels
 * @returns The marker element
 */
export declare function createMarker(pixelY: number): HTMLElement;
/**
 * Validate state update data
 * @param data - The state data
 * @returns True if valid
 */
export declare function isValidStateUpdate(data: unknown): boolean;
/**
 * Parse WebSocket message data
 * @param message - The raw message data
 * @returns Parsed data or null if invalid
 */
export declare function parseWebSocketMessage(message: string): WebSocketData | null;
/**
 * Calculate reconnection delay with exponential backoff
 * @param attempts - Number of reconnection attempts
 * @returns Delay in milliseconds
 */
export declare function calculateReconnectDelay(attempts: number): number;
/**
 * Check if state update is newer than current
 * @param newData - New state data
 * @param currentTimestamp - Current timestamp
 * @returns True if newer
 */
export declare function isNewerState(newData: StateUpdate, currentTimestamp: number): boolean;
//# sourceMappingURL=viewer-utils.d.ts.map