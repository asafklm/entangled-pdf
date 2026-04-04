/**
 * EntangledPdf Viewer - PDF Renderer
 *
 * Handles loading and rendering PDF documents using PDF.js.
 */

// @ts-ignore - Browser module import, resolved at runtime
import * as pdfjsLib from '/pdfjs/pdf.mjs';
import type { PDFPageProxy, PDFDocumentProxy } from '../types/pdfjs';
import type { CanvasWithStyle } from './types';

/**
 * PDF rendering options
 */
export interface PDFRenderOptions {
  minScale?: number;
  padding?: number;
}

/**
 * Rendered page information
 */
export interface RenderedPage {
  wrapper: HTMLElement;
  canvas: HTMLCanvasElement;
  scale: number;
}

/**
 * PDF rendering result
 */
export interface PDFRenderResult {
  document: PDFDocumentProxy;
  pages: Map<number, RenderedPage>;
}

/**
 * PDF Renderer class
 */
export class PDFRenderer {
  private container: HTMLElement;
  private options: Required<PDFRenderOptions>;
  private currentDocument: PDFDocumentProxy | null = null;
  private pages: Map<number, RenderedPage> = new Map();

  constructor(container: HTMLElement, options: PDFRenderOptions = {}) {
    this.container = container;
    this.options = {
      minScale: options.minScale ?? 1.5,
      padding: options.padding ?? 40,
    };
  }

  /**
   * Get the currently rendered document
   */
  get document(): PDFDocumentProxy | null {
    return this.currentDocument;
  }

  /**
   * Get the rendered pages map
   */
  get renderedPages(): Map<number, RenderedPage> {
    return this.pages;
  }

  /**
   * Get page scale for a specific page
   */
  getPageScale(pageNum: number): number {
    return this.pages.get(pageNum)?.scale ?? 1.0;
  }

  /**
   * Get all page scales as a plain object
   */
  getPageScales(): { [key: number]: number } {
    const scales: { [key: number]: number } = {};
    this.pages.forEach((page, num) => {
      scales[num] = page.scale;
    });
    return scales;
  }

  /**
   * Get all page wrappers as a plain object
   */
  getPageElements(): { [key: number]: HTMLElement } {
    const elements: { [key: number]: HTMLElement } = {};
    this.pages.forEach((page, num) => {
      elements[num] = page.wrapper;
    });
    return elements;
  }

  /**
   * Get canvas for a specific page
   */
  getCanvas(pageNum: number): CanvasWithStyle | null {
    const page = this.pages.get(pageNum);
    return page?.canvas as CanvasWithStyle | null;
  }

  /**
   * Load and render a PDF document
   * @param url - The PDF URL
   * @returns Render result with document and pages
   */
  async load(url: string): Promise<PDFRenderResult> {
    // Clear existing content
    this.container.innerHTML = '';
    this.pages.clear();

    // Load the PDF
    const doc = await pdfjsLib.getDocument(url).promise;
    this.currentDocument = doc;

    const dpr = window.devicePixelRatio || 1;
    const containerWidth = this.container.clientWidth - this.options.padding;

    // Render each page
    for (let i = 1; i <= doc.numPages; i++) {
      const page = await doc.getPage(i);
      const renderedPage = await this.renderPage(page, containerWidth, dpr);
      this.pages.set(i, renderedPage);
    }

    return {
      document: doc,
      pages: this.pages,
    };
  }

  /**
   * Render a single page
   */
  private async renderPage(
    page: PDFPageProxy,
    containerWidth: number,
    dpr: number
  ): Promise<RenderedPage> {
    const pageWidthAt1x = page.getViewport({ scale: 1.0 }).width;
    const fitScale = containerWidth / pageWidthAt1x;
    const scale = Math.max(this.options.minScale, fitScale);

    const viewport = page.getViewport({ scale });

    // Create wrapper
    const wrapper = document.createElement('div');
    wrapper.className = 'page-wrapper';

    // Create canvas
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');

    if (!context) {
      throw new Error('Failed to get 2D context from canvas');
    }

    const canvasWidth = Math.round(viewport.width * dpr);
    const canvasHeight = Math.round(viewport.height * dpr);

    canvas.width = canvasWidth;
    canvas.height = canvasHeight;
    canvas.style.width = Math.round(viewport.width) + 'px';
    canvas.style.height = Math.round(viewport.height) + 'px';

    wrapper.appendChild(canvas);
    this.container.appendChild(wrapper);

    // Apply DPR transform
    const transform = dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : null;

    // Render the page
    await page.render({
      canvasContext: context,
      viewport: viewport,
      transform: transform ?? undefined,
    }).promise;

    return {
      wrapper,
      canvas,
      scale,
    };
  }

  /**
   * Clear the renderer and remove all pages
   */
  clear(): void {
    this.container.innerHTML = '';
    this.pages.clear();
    this.currentDocument = null;
  }

  /**
   * Find which page contains a given Y coordinate
   * @param clientY - Y coordinate relative to viewport
   * @returns Page number or null if not found
   */
  findPageAtY(clientY: number): number | null {
    for (const [pageNum, page] of this.pages) {
      const rect = page.wrapper.getBoundingClientRect();
      if (clientY >= rect.top && clientY <= rect.bottom) {
        return pageNum;
      }
    }
    return null;
  }

  /**
   * Get page element at a specific viewport position
   */
  getPageAtPosition(clientX: number, clientY: number): RenderedPage | null {
    for (const [pageNum, page] of this.pages) {
      const rect = page.wrapper.getBoundingClientRect();
      if (
        clientY >= rect.top &&
        clientY <= rect.bottom &&
        clientX >= rect.left &&
        clientX <= rect.right
      ) {
        return page;
      }
    }
    return null;
  }
}

/**
 * Factory function to create PDF URL with cache busting
 */
export function createPDFUrl(baseUrl: string, mtime: number): string {
  return `${baseUrl}?v=${mtime}`;
}

/**
 * Initialize PDF.js worker
 */
export function initPDFJSWorker(workerUrl: string): void {
  pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;
}
