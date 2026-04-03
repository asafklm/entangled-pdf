/**
 * PdfServer Viewer - Core Types
 *
 * Shared type definitions for the PDF viewer modules.
 */

/**
 * PDF position in page coordinates
 */
export interface PdfPosition {
  page: number;
  x: number;
  y: number;
}

/**
 * Viewport position in screen coordinates
 */
export interface ViewportPosition {
  clientX: number;
  clientY: number;
}

/**
 * Canvas element with required style property
 */
export interface CanvasWithStyle extends HTMLCanvasElement {
  style: CSSStyleDeclaration;
}

/**
 * Mock canvas interface for testing
 */
export interface MockCanvas {
  style: { height: string; width?: string };
  height: number;
  width?: number;
}

/**
 * State update data structure
 */
export interface StateUpdate {
  pdf_loaded?: boolean;
  pdf_file?: string;  // Full path from /state endpoint
  pdf_basename?: string;  // Basename from /state endpoint
  pdf_mtime?: number;
  page: number;
  x?: number;
  y?: number;
  last_sync_time?: number;
  action?: string;
}

/**
 * Configuration from server
 */
export interface PDFConfig {
  port: number;
  filename: string;
  mtime: number;
  token: string | null;
  inverse_search_enabled: boolean;
}

/**
 * Global window augmentation
 */
declare global {
  interface Window {
    PDF_CONFIG: PDFConfig;
  }
}

/**
 * Viewer state container
 */
export interface ViewerState {
  page: number | null;
  y: number | null;
  pdfMtime: number;
  lastSyncTime: number;
  pdfLoaded: boolean;
  pendingUpdate: StateUpdate | null;
}

/**
 * Scroll options for scrollToPage
 */
export interface ScrollOptions {
  pageNum: number;
  y?: number;
  attempt?: number;
  showMarker?: boolean;
  markerDelay?: number;
  behavior?: ScrollBehavior;
}

/**
 * Long press state
 */
export interface LongPressState {
  timer: number | null;
  startPos: ViewportPosition | null;
}

/**
 * WebSocket message types
 */
export type WebSocketAction = 
  | 'synctex'
  | 'reload'
  | 'inverse_search'
  | 'ping'
  | 'pong'
  | 'log'
  | 'error';

/**
 * WebSocket message structure
 */
export interface WebSocketMessage {
  action: WebSocketAction;
  page?: number;
  x?: number;
  y?: number;
  last_sync_time?: number;  // When last forward sync occurred
  pdf_mtime?: number;
  pdf_file?: string;  // PDF filename (basename) for reload/synctex messages
  message?: string;
  timestamp?: number;  // Used only for ping/pong RTT calculation
}

/**
 * Error severity levels
 */
export type ErrorSeverity = 'info' | 'warning' | 'error' | 'success';
