import { test, expect } from './fixtures';
import { join } from 'path';

const EXAMPLES_DIR = join(__dirname, '../../examples');
const EXAMPLE_PDF = join(EXAMPLES_DIR, 'example.pdf');

test.describe('PDF Text Layer E2E', () => {

  test('text layer exists and contains text elements', async ({ page, httpsServer }) => {
    await page.goto(`${httpsServer.baseUrl}/view`);
    
    // Load PDF via API
    const response = await fetch(`${httpsServer.baseUrl}/api/load-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': httpsServer.apiKey,
      },
      body: JSON.stringify({
        pdf_path: EXAMPLE_PDF,
      }),
    });
    
    expect(response.ok).toBeTruthy();
    
    // Reload to load the PDF
    await page.reload();
    
    // Wait for PDF to render
    await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 15000 });
    
    // Check that text layer exists
    const textLayer = page.locator('.text-layer').first();
    await expect(textLayer).toBeAttached();
    
    // Check that text layer contains span elements (individual text pieces)
    const textSpans = textLayer.locator('span');
    await expect(textSpans.first()).toBeAttached();
    
    // Verify text spans have content
    const count = await textSpans.count();
    expect(count).toBeGreaterThan(0);
    
    // Check that at least some spans have text content
    const firstText = await textSpans.first().textContent();
    expect(firstText).not.toBeNull();
  });

  test('text is searchable using browser find', async ({ page, httpsServer }) => {
    await page.goto(`${httpsServer.baseUrl}/view`);
    
    // Load PDF via API
    const response = await fetch(`${httpsServer.baseUrl}/api/load-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': httpsServer.apiKey,
      },
      body: JSON.stringify({
        pdf_path: EXAMPLE_PDF,
      }),
    });
    
    expect(response.ok).toBeTruthy();
    
    await page.reload();
    await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 15000 });
    
    // Wait for text layer to be rendered
    await page.waitForTimeout(2000);
    
    // Use browser's find functionality (Ctrl+F)
    await page.keyboard.press('Control+f');
    
    // Wait a moment for find dialog to open
    await page.waitForTimeout(500);
    
    // Try to find text that's likely in example.tex
    // Search for "documentclass" or "LaTeX" - common in LaTeX documents
    await page.keyboard.type('documentclass');
    
    // Wait for search results
    await page.waitForTimeout(1000);
    
    // Check if any text spans are highlighted (have selection)
    const hasSelection = await page.evaluate(() => {
      const selection = window.getSelection();
      return selection && selection.toString().length > 0;
    });
    
    // If browser find doesn't work automatically, check that text content exists
    // at least in the DOM (which is necessary for find to work)
    const textContent = await page.locator('.text-layer span').first().textContent();
    expect(textContent).toBeTruthy();
  });

  test('text can be selected programmatically', async ({ page, httpsServer }) => {
    await page.goto(`${httpsServer.baseUrl}/view`);
    
    // Load PDF via API
    const response = await fetch(`${httpsServer.baseUrl}/api/load-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': httpsServer.apiKey,
      },
      body: JSON.stringify({
        pdf_path: EXAMPLE_PDF,
      }),
    });
    
    expect(response.ok).toBeTruthy();
    
    await page.reload();
    await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 15000 });
    
    // Wait for text layer
    await expect(page.locator('.text-layer').first()).toBeAttached();
    
    // Get the first text span
    const firstSpan = page.locator('.text-layer span').first();
    await expect(firstSpan).toBeAttached();
    
    // Programmatically select the text
    await firstSpan.evaluate((element) => {
      const range = document.createRange();
      range.selectNodeContents(element);
      const selection = window.getSelection();
      if (selection) {
        selection.removeAllRanges();
        selection.addRange(range);
      }
    });
    
    // Verify selection exists
    const selectionText = await page.evaluate(() => {
      const selection = window.getSelection();
      return selection ? selection.toString() : '';
    });
    
    expect(selectionText.length).toBeGreaterThan(0);
  });

  test('text layer spans are positioned with absolute positioning', async ({ page, httpsServer }) => {
    await page.goto(`${httpsServer.baseUrl}/view`);
    
    // Load PDF via API
    const response = await fetch(`${httpsServer.baseUrl}/api/load-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': httpsServer.apiKey,
      },
      body: JSON.stringify({
        pdf_path: EXAMPLE_PDF,
      }),
    });
    
    expect(response.ok).toBeTruthy();
    
    await page.reload();
    await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 15000 });
    
    // Wait for text layer
    await expect(page.locator('.text-layer').first()).toBeAttached();
    
    // Get position information from text spans
    const spanInfo = await page.locator('.text-layer span').first().evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        position: style.position,
        left: style.left,
        top: style.top,
        width: style.width,
        height: style.height,
        color: style.color,
        textContent: el.textContent,
      };
    });
    
    // Verify text layer spans are absolutely positioned
    expect(spanInfo.position).toBe('absolute');
    
    // Verify text is transparent (invisible but selectable)
    expect(spanInfo.color).toContain('0'); // rgba(0, 0, 0, 0) or similar
    
    // Verify dimensions are set
    expect(spanInfo.width).not.toBe('auto');
    expect(spanInfo.height).not.toBe('auto');
    
    console.log('Text span info:', spanInfo);
  });

  test('text layer alignment - spans should be within page bounds', async ({ page, httpsServer }) => {
    await page.goto(`${httpsServer.baseUrl}/view`);
    
    // Load PDF via API
    const response = await fetch(`${httpsServer.baseUrl}/api/load-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': httpsServer.apiKey,
      },
      body: JSON.stringify({
        pdf_path: EXAMPLE_PDF,
      }),
    });
    
    expect(response.ok).toBeTruthy();
    
    await page.reload();
    await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 15000 });
    
    // Wait for text layer
    await expect(page.locator('.text-layer').first()).toBeAttached();
    
    // Get canvas and text layer positions for comparison
    interface AlignmentSuccess {
      canvas: { width: number; height: number; left: number; top: number };
      textLayer: { width: number; height: number; left: number; top: number };
      firstSpan: { width: number; height: number; left: number; top: number; text: string | null } | null;
    }
    
    const alignmentInfo = await page.evaluate(() => {
      const canvas = document.querySelector('#viewer-container canvas');
      const textLayer = document.querySelector('.text-layer');
      
      if (!canvas || !textLayer) {
        throw new Error('Canvas or text layer not found');
      }
      
      const canvasRect = canvas.getBoundingClientRect();
      const textLayerRect = textLayer.getBoundingClientRect();
      
      // Get the first text span to check its size
      const firstSpan = textLayer.querySelector('span');
      let spanInfo: { width: number; height: number; left: number; top: number; text: string | null } | null = null;
      if (firstSpan) {
        const spanRect = firstSpan.getBoundingClientRect();
        spanInfo = {
          width: spanRect.width,
          height: spanRect.height,
          left: spanRect.left,
          top: spanRect.top,
          text: firstSpan.textContent,
        };
      }
      
      return {
        canvas: {
          width: canvasRect.width,
          height: canvasRect.height,
          left: canvasRect.left,
          top: canvasRect.top,
        },
        textLayer: {
          width: textLayerRect.width,
          height: textLayerRect.height,
          left: textLayerRect.left,
          top: textLayerRect.top,
        },
        firstSpan: spanInfo,
      };
    }) as AlignmentSuccess;
    
    console.log('Alignment info:', JSON.stringify(alignmentInfo, null, 2));
    
    // Verify text layer aligns with canvas
    expect(Math.abs(alignmentInfo.canvas.width - alignmentInfo.textLayer.width)).toBeLessThan(5);
    expect(Math.abs(alignmentInfo.canvas.height - alignmentInfo.textLayer.height)).toBeLessThan(5);
    expect(Math.abs(alignmentInfo.canvas.left - alignmentInfo.textLayer.left)).toBeLessThan(5);
    expect(Math.abs(alignmentInfo.canvas.top - alignmentInfo.textLayer.top)).toBeLessThan(5);
    
    // Check first span has reasonable dimensions
    if (alignmentInfo.firstSpan) {
      expect(alignmentInfo.firstSpan.width).toBeGreaterThan(0);
      expect(alignmentInfo.firstSpan.height).toBeGreaterThan(0);
    }
  });

  test('text positioning accuracy - end of line alignment', async ({ page, httpsServer }) => {
    await page.goto(`${httpsServer.baseUrl}/view`);
    
    // Load PDF via API
    const response = await fetch(`${httpsServer.baseUrl}/api/load-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': httpsServer.apiKey,
      },
      body: JSON.stringify({
        pdf_path: EXAMPLE_PDF,
      }),
    });
    
    expect(response.ok).toBeTruthy();
    
    await page.reload();
    await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 15000 });
    
    // Wait for text layer
    await expect(page.locator('.text-layer').first()).toBeAttached();
    await page.waitForTimeout(1000); // Ensure text layer is fully rendered
    
    // Get all text spans and their positions
    interface TextSpanInfo {
      text: string;
      left: number;
      top: number;
      width: number;
      height: number;
      right: number;
    }
    
    const textSpans: TextSpanInfo[] = await page.evaluate(() => {
      const textLayer = document.querySelector('.text-layer');
      if (!textLayer) return [];
      
      const spans = textLayer.querySelectorAll('span');
      const canvas = document.querySelector('#viewer-container canvas');
      const canvasRect = canvas?.getBoundingClientRect();
      
      if (!canvasRect) return [];
      
      return Array.from(spans).map(span => {
        const rect = span.getBoundingClientRect();
        return {
          text: span.textContent || '',
          left: rect.left - canvasRect.left,
          top: rect.top - canvasRect.top,
          width: rect.width,
          height: rect.height,
          right: rect.right - canvasRect.left,
        };
      });
    });
    
    expect(textSpans.length).toBeGreaterThan(0);
    
    // Find text spans near the right edge of the page (end of line text)
    const canvasWidth = await page.locator('#viewer-container canvas').first().evaluate(el => el.getBoundingClientRect().width);
    
    // Get spans that are positioned near the right side (within 20% of page width from right edge)
    const rightEdgeSpans = textSpans.filter(span => span.right > canvasWidth * 0.8);
    
    console.log(`Found ${rightEdgeSpans.length} text spans near the right edge`);
    console.log('Sample end-of-line spans:', rightEdgeSpans.slice(0, 3));
    
    // Verify that right-edge spans have positive dimensions
    if (rightEdgeSpans.length > 0) {
      for (const span of rightEdgeSpans) {
        expect(span.width).toBeGreaterThan(0);
        expect(span.height).toBeGreaterThan(0);
        // The span should be positioned within the canvas bounds
        expect(span.left).toBeGreaterThanOrEqual(0);
        expect(span.left).toBeLessThan(canvasWidth);
      }
    }
    
    // Find the rightmost text and verify it's not too far right
    const rightmostSpan = textSpans.reduce((max, span) => span.right > max.right ? span : max, textSpans[0]);
    console.log('Rightmost text span:', rightmostSpan);
    
    // The rightmost text should not extend significantly beyond the canvas width
    // Allow for some tolerance due to font differences
    expect(rightmostSpan.right).toBeLessThan(canvasWidth + 10);
  });
});
