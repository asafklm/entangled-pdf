/**
 * PdfServer Viewer - Client Logger
 *
 * Logs browser-initiated events (scrolls, PDF loads) and sends to server via WebSocket.
 * Rate limited to prevent log spam (max 100 logs per second).
 */

import type { WebSocketManager } from './websocket-manager';

/**
 * Position information for scroll logging
 */
interface ScrollPosition {
  page: number;
  y: number;
  pixels: number;
}

/**
 * Rate limiter configuration
 */
const MAX_LOGS_PER_SECOND = 100;
const RATE_LIMIT_WINDOW_MS = 1000;

/**
 * Client-side event logger with rate limiting
 */
export class ClientLogger {
  private wsManager: WebSocketManager | null = null;
  private logCount = 0;
  private windowStart = Date.now();

  /**
   * Attach WebSocket manager for sending logs to server
   */
  attachWebSocket(wsManager: WebSocketManager): void {
    this.wsManager = wsManager;
  }

  /**
   * Check if we're within rate limits
   */
  private checkRateLimit(): boolean {
    const now = Date.now();
    
    // Reset counter if window has passed
    if (now - this.windowStart >= RATE_LIMIT_WINDOW_MS) {
      this.logCount = 0;
      this.windowStart = now;
    }
    
    // Check if we can log
    if (this.logCount >= MAX_LOGS_PER_SECOND) {
      return false;
    }
    
    this.logCount++;
    return true;
  }

  /**
   * Send log to server via WebSocket
   */
  private sendToServer(message: string): void {
    if (!this.wsManager) {
      return;
    }

    this.wsManager.send({
      action: 'log',
      message,
      timestamp: Date.now(),
    });
  }

  /**
   * Log a scroll event
   * Format: [scroll] from: page X, y=Y (Zpixels) to: page A, y=B (Cpixels)
   */
  logScroll(from: ScrollPosition, to: ScrollPosition): void {
    if (!this.checkRateLimit()) {
      return;
    }

    const fromStr = `page ${from.page}, y=${from.y.toFixed(2)} (${Math.round(from.pixels)}px)`;
    const toStr = `page ${to.page}, y=${to.y.toFixed(2)} (${Math.round(to.pixels)}px)`;
    const logMessage = `[scroll] from: ${fromStr} to: ${toStr}`;

    // Log locally
    console.log(logMessage);

    // Send to server
    this.sendToServer(logMessage);
  }

  /**
   * Log a PDF load event
   * Format: [loaded] <filename> (mtime: timestamp)
   */
  logPdfLoad(filename: string, mtime: number): void {
    if (!this.checkRateLimit()) {
      return;
    }

    const logMessage = `[loaded] ${filename} (mtime: ${mtime})`;

    // Log locally
    console.log(logMessage);

    // Send to server
    this.sendToServer(logMessage);
  }

  /**
   * Get current scroll information from container and renderer
   */
  getCurrentPosition(
    container: HTMLElement,
    pdfRenderer: {
      findPageAtY: (y: number) => number | null;
      renderedPages: Map<number, { wrapper: HTMLElement }>;
    }
  ): ScrollPosition | null {
    const scrollTop = container.scrollTop;
    const pageNum = pdfRenderer.findPageAtY(scrollTop);
    
    if (!pageNum) {
      return null;
    }

    const page = pdfRenderer.renderedPages.get(pageNum);
    if (!page) {
      return null;
    }

    // Calculate Y position within the page (in PDF points)
    const pageTop = page.wrapper.offsetTop;
    const offsetInPage = scrollTop - pageTop;
    // This is an approximation - actual PDF points would need scale factor
    const yInPdfPoints = offsetInPage; // Simplified, could be improved with actual scale

    return {
      page: pageNum,
      y: yInPdfPoints,
      pixels: scrollTop,
    };
  }
}

/**
 * Singleton instance
 */
export const clientLogger = new ClientLogger();
