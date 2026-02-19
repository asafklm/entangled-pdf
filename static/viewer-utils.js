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
 * @param {HTMLCanvasElement} canvas - The canvas element
 * @returns {number} Render scale factor
 */
export function getRenderScale(canvas) {
    const cssHeight = parseFloat(canvas.style.height);
    const internalHeight = canvas.height;
    const dpr = window.devicePixelRatio || 1;
    return (cssHeight * dpr) / internalHeight;
}

/**
 * Convert PDF y-coordinate to CSS pixels
 * @param {HTMLCanvasElement} canvas - The canvas element
 * @param {number} y - Y coordinate in PDF points
 * @returns {number} Pixel Y coordinate
 */
export function pdfYToPixels(canvas, y) {
    return y * getRenderScale(canvas);
}

/**
 * Calculate scroll position for a given page and y-coordinate
 * @param {HTMLElement} container - The scroll container
 * @param {HTMLElement} target - The target page element
 * @param {HTMLCanvasElement} canvas - The canvas element
 * @param {number} y - Y coordinate in PDF points
 * @returns {number} The scroll top position
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
 * @param {number} pixelY - Y position in pixels
 * @returns {HTMLElement} The marker element
 */
export function createMarker(pixelY) {
    const marker = document.createElement('div');
    marker.className = 'synctex-marker';
    marker.style.top = (pixelY - MARKER_OFFSET) + 'px';
    return marker;
}

/**
 * Validate state update data
 * @param {Object} data - The state data
 * @returns {boolean} True if valid
 */
export function isValidStateUpdate(data) {
    return data && 
           typeof data === 'object' && 
           typeof data.page === 'number' &&
           data.page > 0;
}

/**
 * Parse WebSocket message data
 * @param {string} message - The raw message data
 * @returns {Object|null} Parsed data or null if invalid
 */
export function parseWebSocketMessage(message) {
    try {
        return JSON.parse(message);
    } catch (e) {
        return null;
    }
}

/**
 * Calculate reconnection delay with exponential backoff
 * @param {number} attempts - Number of reconnection attempts
 * @returns {number} Delay in milliseconds
 */
export function calculateReconnectDelay(attempts) {
    return Math.min(1000 * Math.pow(2, attempts), MAX_RECONNECT_DELAY);
}

/**
 * Check if state update is newer than current
 * @param {Object} newData - New state data
 * @param {number} currentTimestamp - Current timestamp
 * @returns {boolean} True if newer
 */
export function isNewerState(newData, currentTimestamp) {
    const newTimestamp = newData.timestamp || newData.last_update_time || 0;
    return newTimestamp > currentTimestamp;
}
