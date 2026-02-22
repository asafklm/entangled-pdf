/**
 * Type declarations for PDF.js library
 * Minimal types for the functionality used in this project
 */

export interface PDFViewport {
  width: number;
  height: number;
}

export interface PDFPageProxy {
  getViewport(options: { scale: number }): PDFViewport;
  render(options: {
    canvasContext: CanvasRenderingContext2D;
    viewport: PDFViewport;
    transform?: number[] | null;
  }): { promise: Promise<void> };
}

export interface PDFDocumentProxy {
  numPages: number;
  getPage(pageNumber: number): Promise<PDFPageProxy>;
}

export interface PDFGetDocumentOptions {
  promise: Promise<PDFDocumentProxy>;
}

export interface PDFJSGlobal {
  GlobalWorkerOptions: {
    workerSrc: string;
  };
  getDocument(url: string): PDFGetDocumentOptions;
}

declare global {
  const pdfjsLib: PDFJSGlobal;
}
