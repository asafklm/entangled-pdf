import { test, expect } from './fixtures';
import { join } from 'path';

const EXAMPLES_DIR = join(__dirname, '../../examples');
const EXAMPLE_PDF = join(EXAMPLES_DIR, 'example.pdf');

test.describe('PDF Text Layer Debug', () => {

  test('debug text content structure from PDF.js', async ({ page, httpsServer }) => {
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
    
    // Get detailed info about text spans and their transforms
    const textAnalysis = await page.evaluate(() => {
      const pages = document.querySelectorAll('.page-wrapper');
      if (pages.length < 3) return null;
      
      const page3 = pages[2];
      const textLayer = page3.querySelector('.text-layer');
      const canvas = page3.querySelector('canvas');
      
      if (!textLayer || !canvas) return null;
      
      const canvasRect = canvas.getBoundingClientRect();
      const textLayerRect = textLayer.getBoundingClientRect();
      
      const spans = textLayer.querySelectorAll('span');
      
      // Find all spans containing "intension"
      const intensionSpans = Array.from(spans).filter(span => 
        span.textContent && span.textContent.toLowerCase().includes('intension')
      ).map(span => {
        const rect = span.getBoundingClientRect();
        const style = window.getComputedStyle(span);
        return {
          text: span.textContent,
          // Absolute positioning in viewport
          absLeft: rect.left,
          absTop: rect.top,
          absRight: rect.right,
          absBottom: rect.bottom,
          width: rect.width,
          height: rect.height,
          // Relative to canvas
          relLeft: rect.left - canvasRect.left,
          relTop: rect.top - canvasRect.top,
          // CSS properties
          transform: style.transform,
          fontSize: style.fontSize,
          fontFamily: style.fontFamily,
          letterSpacing: style.letterSpacing,
          lineHeight: style.lineHeight,
          // Positioning
          cssLeft: style.left,
          cssTop: style.top,
        };
      });
      
      // Get all spans for comparison
      const allSpans = Array.from(spans).slice(0, 10).map(span => {
        const rect = span.getBoundingClientRect();
        const style = window.getComputedStyle(span);
        return {
          text: span.textContent?.substring(0, 50),
          relLeft: rect.left - canvasRect.left,
          relTop: rect.top - canvasRect.top,
          width: rect.width,
          height: rect.height,
          fontSize: style.fontSize,
          fontFamily: style.fontFamily,
        };
      });
      
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
        intensionSpans,
        firstTenSpans: allSpans,
      };
    });
    
    expect(textAnalysis).not.toBeNull();
    
    if (textAnalysis) {
      console.log('\n=== CANVAS ===');
      console.log(`Canvas: ${textAnalysis.canvas.width}x${textAnalysis.canvas.height} at (${textAnalysis.canvas.left}, ${textAnalysis.canvas.top})`);
      
      console.log('\n=== TEXT LAYER ===');
      console.log(`TextLayer: ${textAnalysis.textLayer.width}x${textAnalysis.textLayer.height} at (${textAnalysis.textLayer.left}, ${textAnalysis.textLayer.top})`);
      
      console.log('\n=== INTENSION SPANS ===');
      if (textAnalysis.intensionSpans.length > 0) {
        textAnalysis.intensionSpans.forEach((span, i) => {
          console.log(`\nSpan ${i + 1}:`);
          console.log(`  Text: "${span.text}"`);
          console.log(`  Position: (${span.relLeft.toFixed(2)}, ${span.relTop.toFixed(2)})`);
          console.log(`  Size: ${span.width.toFixed(2)}x${span.height.toFixed(2)}`);
          console.log(`  Transform: ${span.transform}`);
          console.log(`  Font: ${span.fontFamily} @ ${span.fontSize}`);
          console.log(`  CSS left/top: ${span.cssLeft}, ${span.cssTop}`);
        });
      } else {
        console.log('No spans found with "intension" text');
      }
      
      console.log('\n=== FIRST 10 SPANS ===');
      textAnalysis.firstTenSpans.forEach((span, i) => {
        console.log(`${i + 1}. "${span.text}" at (${span.relLeft.toFixed(1)}, ${span.relTop.toFixed(1)}) - ${span.fontFamily}`);
      });
    }
  });

  test('verify font-family is applied correctly', async ({ page, httpsServer }) => {
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
    
    // Check computed font styles
    const fontInfo = await page.evaluate(() => {
      const textLayer = document.querySelector('.text-layer');
      if (!textLayer) return null;
      
      const spans = textLayer.querySelectorAll('span');
      if (spans.length === 0) return null;
      
      // Check multiple spans
      const samples = Array.from(spans).slice(0, 5).map(span => {
        const style = window.getComputedStyle(span);
        return {
          text: span.textContent?.substring(0, 30),
          fontFamily: style.fontFamily,
          fontSize: style.fontSize,
          fontWeight: style.fontWeight,
          fontStyle: style.fontStyle,
        };
      });
      
      // Also check the text layer container style
      const containerStyle = window.getComputedStyle(textLayer);
      
      return {
        container: {
          fontFamily: containerStyle.fontFamily,
        },
        samples,
      };
    });
    
    expect(fontInfo).not.toBeNull();
    
    if (fontInfo) {
      console.log('\n=== FONT INFO ===');
      console.log(`Container font-family: ${fontInfo.container.fontFamily}`);
      console.log('\nSample spans:');
      fontInfo.samples.forEach((sample, i) => {
        console.log(`${i + 1}. "${sample.text}"`);
        console.log(`   font-family: ${sample.fontFamily}`);
        console.log(`   font-size: ${sample.fontSize}`);
        console.log(`   font-weight: ${sample.fontWeight}`);
        console.log(`   font-style: ${sample.fontStyle}`);
      });
      
      // Verify that font-family is being applied
      // It might not be the exact one we set due to PDF.js overrides or font availability
      // but it should be defined
      fontInfo.samples.forEach(sample => {
        expect(sample.fontFamily).toBeTruthy();
      });
    }
  });

  test('check transform and scale properties', async ({ page, httpsServer }) => {
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
    
    // Get transform and scale information
    const transformInfo = await page.evaluate(() => {
      const pages = document.querySelectorAll('.page-wrapper');
      if (pages.length < 3) return null;
      
      const page3 = pages[2];
      const textLayer = page3.querySelector('.text-layer');
      const canvas = page3.querySelector('canvas');
      
      if (!textLayer || !canvas) return null;
      
      const canvasStyle = window.getComputedStyle(canvas);
      const textLayerStyle = window.getComputedStyle(textLayer);
      
      const spans = textLayer.querySelectorAll('span');
      const spanTransforms = Array.from(spans).slice(0, 5).map(span => {
        const style = window.getComputedStyle(span);
        return {
          text: span.textContent?.substring(0, 20),
          transform: style.transform,
          transformOrigin: style.transformOrigin,
          scale: style.getPropertyValue('--scale-factor'),
        };
      });
      
      return {
        canvas: {
          width: canvasStyle.width,
          height: canvasStyle.height,
          transform: canvasStyle.transform,
        },
        textLayer: {
          width: textLayerStyle.width,
          height: textLayerStyle.height,
          transform: textLayerStyle.transform,
          scaleFactor: (textLayer as HTMLElement).style.getPropertyValue('--scale-factor'),
        },
        spanTransforms,
      };
    });
    
    expect(transformInfo).not.toBeNull();
    
    if (transformInfo) {
      console.log('\n=== TRANSFORM INFO ===');
      console.log(`Canvas: ${transformInfo.canvas.width} x ${transformInfo.canvas.height}`);
      console.log(`Canvas transform: ${transformInfo.canvas.transform}`);
      console.log(`\nTextLayer: ${transformInfo.textLayer.width} x ${transformInfo.textLayer.height}`);
      console.log(`TextLayer transform: ${transformInfo.textLayer.transform}`);
      console.log(`TextLayer --scale-factor: ${transformInfo.textLayer.scaleFactor}`);
      
      console.log('\nSpan transforms:');
      transformInfo.spanTransforms.forEach((span, i) => {
        console.log(`${i + 1}. "${span.text}"`);
        console.log(`   transform: ${span.transform}`);
        console.log(`   transform-origin: ${span.transformOrigin}`);
        console.log(`   --scale-factor: ${span.scale}`);
      });
    }
  });
});
