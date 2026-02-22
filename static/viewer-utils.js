/**
 * PdfServer Viewer - Testable Module
 *
 * Extracted functions from viewer.js for unit testing
 */
// Constants
export const ACTION_SYNCTEX = 'synctex';
export const MAX_RECONNECT_DELAY = 30000;
export const POLLING_INTERVAL = 2000;
export const MARKER_DISPLAY_TIME = 5000;
export const MARKER_OFFSET = 5;
/**
 * Calculate render scale from canvas dimensions
 * @param canvas - The canvas element (or mock for testing)
 * @returns Render scale factor
 */
export function getRenderScale(canvas) {
    const cssHeight = parseFloat(canvas.style.height);
    const internalHeight = canvas.height;
    const dpr = window.devicePixelRatio || 1;
    return (cssHeight * dpr) / internalHeight;
}
/**
 * Convert PDF y-coordinate to CSS pixels
 * @param canvas - The canvas element
 * @param y - Y coordinate in PDF points
 * @returns Pixel Y coordinate
 */
export function pdfYToPixels(canvas, y) {
    return y * getRenderScale(canvas);
}
/**
 * Calculate scroll position for a given page and y-coordinate
 * @param container - The scroll container
 * @param target - The target page element
 * @param canvas - The canvas element
 * @param y - Y coordinate in PDF points
 * @returns The scroll top position
 */
export function calculateScrollPosition(container, target, canvas, y) {
    const pixelY = pdfYToPixels(canvas, y);
    const containerStyle = window.getComputedStyle(container);
    const paddingTop = parseFloat(containerStyle.paddingTop) || 20;
    const viewportHeight = container.clientHeight;
    const targetScrollTop = target.offsetTop + pixelY - (viewportHeight / 2) + paddingTop;
    return Math.max(0, Math.round(targetScrollTop));
}
/**
 * Create a marker element at the specified position
 * @param pixelY - Y position in pixels
 * @returns The marker element
 */
export function createMarker(pixelY) {
    const marker = document.createElement('div');
    marker.className = 'synctex-marker';
    marker.style.top = (pixelY - MARKER_OFFSET) + 'px';
    return marker;
}
/**
 * Validate state update data
 * @param data - The state data
 * @returns True if valid
 */
export function isValidStateUpdate(data) {
    return (data !== null &&
        data !== undefined &&
        typeof data === 'object' &&
        'page' in data &&
        typeof data.page === 'number' &&
        data.page > 0);
}
/**
 * Parse WebSocket message data
 * @param message - The raw message data
 * @returns Parsed data or null if invalid
 */
export function parseWebSocketMessage(message) {
    try {
        return JSON.parse(message);
    }
    catch {
        return null;
    }
}
/**
 * Calculate reconnection delay with exponential backoff
 * @param attempts - Number of reconnection attempts
 * @returns Delay in milliseconds
 */
export function calculateReconnectDelay(attempts) {
    return Math.min(1000 * Math.pow(2, attempts), MAX_RECONNECT_DELAY);
}
/**
 * Check if state update is newer than current
 * @param newData - New state data
 * @param currentTimestamp - Current timestamp
 * @returns True if newer
 */
export function isNewerState(newData, currentTimestamp) {
    const newTimestamp = newData.timestamp || newData.last_update_time || 0;
    return newTimestamp > currentTimestamp;
}
//# sourceMappingURL=viewer-utils.js.map