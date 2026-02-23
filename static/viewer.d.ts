/**
 * PdfServer Viewer JavaScript
 *
 * Handles PDF rendering, WebSocket communication, and SyncTeX synchronization.
 */
interface PDFConfig {
    port: number;
    filename: string;
    mtime: number;
}
declare global {
    interface Window {
        PDF_CONFIG: PDFConfig;
    }
}
export {};
//# sourceMappingURL=viewer.d.ts.map