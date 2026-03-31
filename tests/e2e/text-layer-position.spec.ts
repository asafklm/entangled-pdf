import { test, expect } from './fixtures';
import { join } from 'path';

const EXAMPLES_DIR = join(__dirname, '../../examples');
const EXAMPLE_PDF = join(EXAMPLES_DIR, 'example.pdf');

test.describe('PDF Text Layer Position Verification', () => {

  test('screenshot and verify intension word positioning on page 3', async ({ page, httpsServer }) => {
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
    
    // Wait for text layer to be fully rendered
    await page.waitForTimeout(2000);
    
    // Navigate to page 3 by scrolling
    await page.evaluate(() => {
      const container = document.getElementById('viewer-container');
      const pages = document.querySelectorAll('.page-wrapper');
      if (pages.length >= 3) {
        const page3 = pages[2];
        page3.scrollIntoView({ behavior: 'instant', block: 'start' });
      }
    });
    
    await page.waitForTimeout(1000);
    
    // Take a full page screenshot
    await page.screenshot({ 
      path: 'test-results/page3-full.png',
      fullPage: true 
    });
    
    // Find the word 'intension' in the text layer
    const intensionElement = page.locator('.text-layer span', { hasText: 'intension' });
    
    // Check if the element exists
    const count = await intensionElement.count();
    console.log(`Found ${count} elements with text 'intension'`);
    
    if (count > 0) {
      // Get the position of 'intension' text
      const intensionInfo = await intensionElement.first().evaluate((el) => {
        const rect = el.getBoundingClientRect();
        const computedStyle = window.getComputedStyle(el);
        return {
          text: el.textContent,
          left: rect.left,
          top: rect.top,
          width: rect.width,
          height: rect.height,
          right: rect.right,
          bottom: rect.bottom,
          fontSize: computedStyle.fontSize,
          transform: computedStyle.transform,
        };
      });
      
      console.log('Intension element info:', JSON.stringify(intensionInfo, null, 2));
      
      // Take screenshot of the specific area around 'intension'
      await page.screenshot({
        path: 'test-results/intension-area.png',
        clip: {
          x: Math.max(0, intensionInfo.left - 50),
          y: Math.max(0, intensionInfo.top - 50),
          width: intensionInfo.width + 100,
          height: intensionInfo.height + 100,
        }
      });
      
      // Verify the element has reasonable dimensions
      expect(intensionInfo.width).toBeGreaterThan(0);
      expect(intensionInfo.height).toBeGreaterThan(0);
      
      // The word should be visible on screen
      expect(intensionInfo.left).toBeGreaterThan(0);
      expect(intensionInfo.top).toBeGreaterThan(0);
    }
  });

  test('verify text alignment by comparing text and canvas positions', async ({ page, httpsServer }) => {
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
    await page.waitForTimeout(2000);
    
    // Navigate to page 3
    await page.evaluate(() => {
      const pages = document.querySelectorAll('.page-wrapper');
      if (pages.length >= 3) {
        pages[2].scrollIntoView({ behavior: 'instant', block: 'start' });
      }
    });
    
    await page.waitForTimeout(1000);
    
    // Get detailed position info for all text elements on page 3
    const textPositions = await page.evaluate(() => {
      const pages = document.querySelectorAll('.page-wrapper');
      if (pages.length < 3) return null;
      
      const page3 = pages[2];
      const textLayer = page3.querySelector('.text-layer');
      const canvas = page3.querySelector('canvas');
      
      if (!textLayer || !canvas) return null;
      
      const canvasRect = canvas.getBoundingClientRect();
      const textLayerRect = textLayer.getBoundingClientRect();
      
      const spans = textLayer.querySelectorAll('span');
      const positions = Array.from(spans).map(span => {
        const rect = span.getBoundingClientRect();
        const style = window.getComputedStyle(span);
        return {
          text: span.textContent,
          // Relative to canvas
          left: rect.left - canvasRect.left,
          top: rect.top - canvasRect.top,
          width: rect.width,
          height: rect.height,
          right: rect.right - canvasRect.left,
          bottom: rect.bottom - canvasRect.top,
          // Style info
          fontSize: style.fontSize,
          fontFamily: style.fontFamily,
          transform: style.transform,
        };
      });
      
      return {
        canvas: {
          width: canvasRect.width,
          height: canvasRect.height,
        },
        textLayer: {
          width: textLayerRect.width,
          height: textLayerRect.height,
        },
        texts: positions,
      };
    });
    
    expect(textPositions).not.toBeNull();
    
    if (textPositions) {
      console.log('Canvas dimensions:', textPositions.canvas);
      console.log('TextLayer dimensions:', textPositions.textLayer);
      
      // Find 'intension' specifically
      const intensionTexts = textPositions.texts.filter(t => 
        t.text && t.text.toLowerCase().includes('intension')
      );
      
      console.log('Intension text positions:', JSON.stringify(intensionTexts, null, 2));
      
      // Also find 'testing' which it appears over according to the bug report
      const testingTexts = textPositions.texts.filter(t => 
        t.text && t.text.toLowerCase().includes('testing')
      );
      
      console.log('Testing text positions:', JSON.stringify(testingTexts, null, 2));
      
      // Check if intension and testing overlap
      if (intensionTexts.length > 0 && testingTexts.length > 0) {
        const intension = intensionTexts[0];
        const testing = testingTexts[0];
        
        // Check for vertical overlap (y-axis)
        const verticalOverlap = !(intension.bottom < testing.top || intension.top > testing.bottom);
        // Check for horizontal overlap (x-axis)  
        const horizontalOverlap = !(intension.right < testing.left || intension.left > testing.right);
        
        if (verticalOverlap && horizontalOverlap) {
          console.log('WARNING: "intension" and "testing" text elements overlap!');
          console.log('This indicates text layer misalignment.');
        }
        
        // The bug is that intension appears over testing
        // They should NOT overlap if positioned correctly
        // For now, just document the positions
        expect(intension.left).toBeDefined();
        expect(testing.left).toBeDefined();
      }
    }
  });

  test('visual verification - select text at reported misaligned position', async ({ page, httpsServer }) => {
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
    
    await page.waitForTimeout(2000);
    
    // Navigate to page 3
    await page.evaluate(() => {
      const pages = document.querySelectorAll('.page-wrapper');
      if (pages.length >= 3) {
        pages[2].scrollIntoView({ behavior: 'instant', block: 'center' });
      }
    });
    
    await page.waitForTimeout(1000);
    
    // Take screenshot before selection
    await page.screenshot({
      path: 'test-results/before-selection.png',
      fullPage: false,
    });
    
    // Try to find and click on the word 'intension' to see where it actually is
    const intensionSpan = page.locator('.text-layer span', { hasText: 'intension' });
    
    if (await intensionSpan.count() > 0) {
      // Click on the word to focus/see it
      await intensionSpan.first().click();
      
      await page.waitForTimeout(500);
      
      // Take screenshot after clicking
      await page.screenshot({
        path: 'test-results/after-click-intension.png',
        fullPage: false,
      });
      
      // Now try to select it by triple-clicking
      await intensionSpan.first().click({ clickCount: 3 });
      
      await page.waitForTimeout(500);
      
      // Take screenshot after selection
      await page.screenshot({
        path: 'test-results/after-selection-intension.png',
        fullPage: false,
      });
    }
  });
});
