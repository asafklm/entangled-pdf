# Implementation Plan: Text Layer for Search/Select Feature

## Branch
`feature/text-search` (created from main)

## Phase 1: Type Definitions (types/pdfjs.d.ts)

Add the following types to support TextLayer:

```typescript
// Add to PDFViewport interface:
clone(options: { dontFlip: boolean }): PDFViewport;

// Add to PDFPageProxy interface:
getTextContent(): Promise<TextContent>;

// New interfaces:
export interface TextContent {
  items: TextItem[];
  styles: { [key: string]: TextStyle };
}

export interface TextItem {
  str: string;
  dir: string;
  width: number;
  height: number;
  transform: number[];
  fontName: string;
}

export interface TextStyle {
  fontFamily: string;
  ascent: number;
  descent: number;
  vertical: boolean;
}

export interface TextLayer {
  render(): Promise<void>;
}

export interface TextLayerOptions {
  container: HTMLDivElement;
  textContentSource: TextContent;
  viewport: PDFViewport;
}

// Add to PDFJSGlobal:
TextLayer: new (options: TextLayerOptions) => TextLayer;
```

## Phase 2: PDF Renderer Updates (static/pdf-renderer.ts)

### Update RenderedPage interface:
```typescript
export interface RenderedPage {
  wrapper: HTMLElement;
  canvas: HTMLCanvasElement;
  textLayer: HTMLDivElement;  // ADD
  scale: number;
}
```

### Modify renderPage() method:
After canvas creation and rendering, add:

```typescript
// Create text layer container
const textLayerDiv = document.createElement('div');
textLayerDiv.className = 'text-layer';
wrapper.appendChild(textLayerDiv);

// Get text content and render text layer
const textContent = await page.getTextContent();
const textLayer = new pdfjsLib.TextLayer({
  container: textLayerDiv,
  textContentSource: textContent,
  viewport: viewport.clone({ dontFlip: true }),
});
await textLayer.render();
```

### Update return object:
```typescript
return {
  wrapper,
  canvas,
  textLayer: textLayerDiv,  // ADD
  scale,
};
```

## Phase 3: CSS Styling (static/viewer.html)

Add within the `<style>` tag:

```css
/* Page wrapper needs relative positioning for text layer positioning */
.page-wrapper {
    display: inline-block;
    margin: 0 auto 20px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.6);
    max-width: 100%;
    position: relative;  /* ADD: for absolute positioning context */
}

/* Text layer for selectable text */
.text-layer {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 5;
    cursor: text;
}

.text-layer span {
    position: absolute;
    color: transparent;
    white-space: pre;
    user-select: text;
    -webkit-user-select: text;
    pointer-events: auto;
}
```

## Phase 4: Testing (Deferred to Phase 2)

### E2E Test Plan (tests/e2e/text-selection.spec.ts)

Tests to verify after implementation:
1. **Text layer presence**: Verify `.text-layer` div exists for each page
2. **Text alignment**: Compare text position with rendered PDF content
3. **Text selection**: Drag to highlight text across words/lines
4. **Copy functionality**: Ctrl+C copies selected text to clipboard
5. **Browser find**: Ctrl+F finds text in the document
6. **Performance**: Measure render time with/without text layer

### Implementation Concerns (User Noted)
- Text alignment accuracy is the primary concern
- May need iteration on positioning/scaling logic
- E2E tests will validate and may require adjustments

## Performance Notes
- Text extraction: ~1-2ms per page (single call to getTextContent)
- DOM elements: Lightweight positioned spans, no event listeners
- No additional network requests
- Estimated overhead: <5% of total render time

## Files Modified
1. `types/pdfjs.d.ts` - Add TextLayer types
2. `static/pdf-renderer.ts` - Implement text layer rendering
3. `static/viewer.html` - Add text layer CSS

## Accessibility
No aria-label needed per user requirement - this is a convenience feature for LaTeX users who have access to source text.
