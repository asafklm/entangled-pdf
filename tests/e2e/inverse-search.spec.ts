import { test, expect } from './fixtures';
import { join } from 'path';

const EXAMPLES_DIR = join(__dirname, '../../examples');
const EXAMPLE_PDF = join(EXAMPLES_DIR, 'example.pdf');

test.describe('Inverse Search E2E', () => {
  test.describe('HTTPS with Inverse Search Enabled', () => {
    test('inverse search is enabled on server', async ({ httpsInverseServer }) => {
      const response = await fetch(`${httpsInverseServer.baseUrl}/state`);
      const data = await response.json();
      
      expect(data.inverse_search_enabled).toBeTruthy();
    });

    test('viewer includes inverse search UI elements', async ({ page, httpsInverseServer }) => {
      await fetch(`${httpsInverseServer.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': httpsInverseServer.apiKey,
        },
        body: JSON.stringify({
          pdf_path: EXAMPLE_PDF,
        }),
      });
      
      const stateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
      const stateData = await stateResponse.json();
      const token = stateData.websocket_token;
      
      await page.context().addCookies([{
        name: 'pdf_token',
        value: token,
        domain: 'localhost',
        path: '/',
        secure: true,
        httpOnly: true,
        sameSite: 'Strict',
      }]);
      
      await page.goto(`${httpsInverseServer.baseUrl}/view`);
      
      await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 10000 });
      
      await expect(page.locator('#connection-status')).toBeVisible({ timeout: 5000 });
    });

    test('long-press shows inverse search tooltip with confirmation', async ({ page, httpsInverseServer }) => {
      // Load the PDF
      await fetch(`${httpsInverseServer.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': httpsInverseServer.apiKey,
        },
        body: JSON.stringify({
          pdf_path: EXAMPLE_PDF,
        }),
      });
      
      // Get auth token and set cookie
      const stateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
      const stateData = await stateResponse.json();
      const token = stateData.websocket_token;
      
      await page.context().addCookies([{
        name: 'pdf_token',
        value: token,
        domain: 'localhost',
        path: '/',
        secure: true,
        httpOnly: true,
        sameSite: 'Strict',
      }]);
      
      await page.goto(`${httpsInverseServer.baseUrl}/view`);
      
      // Wait for PDF to render
      await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 10000 });
      
      // Long-press on the PDF canvas to trigger inverse search (hold for 600ms)
      const canvas = page.locator('#viewer-container canvas').first();
      await canvas.hover();
      await canvas.dispatchEvent('mousedown');
      await page.waitForTimeout(600); // Wait longer than the 500ms threshold
      await canvas.dispatchEvent('mouseup');
      
      // Wait for tooltip to appear
      const tooltip = page.locator('.inverse-search-tooltip');
      await expect(tooltip).toBeVisible({ timeout: 5000 });
      
      // Verify tooltip content
      await expect(tooltip.locator('text=Go to Source?')).toBeVisible();
      await expect(tooltip.locator('button.tooltip-btn-confirm')).toContainText('Confirm (Enter)');
      
      // Click the confirm button (same code path as Enter key)
      await tooltip.locator('button.tooltip-btn-confirm').click();
      
      // Wait for tooltip to disappear
      await expect(tooltip).not.toBeVisible({ timeout: 5000 });
      
      // Verify red marker feedback is shown
      const marker = page.locator('.synctex-marker');
      await expect(marker).toBeVisible({ timeout: 5000 });
    });

    test('long-press tooltip can be dismissed with Escape key', async ({ page, httpsInverseServer }) => {
      // Load the PDF
      await fetch(`${httpsInverseServer.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': httpsInverseServer.apiKey,
        },
        body: JSON.stringify({
          pdf_path: EXAMPLE_PDF,
        }),
      });
      
      // Get auth token and set cookie
      const stateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
      const stateData = await stateResponse.json();
      const token = stateData.websocket_token;
      
      await page.context().addCookies([{
        name: 'pdf_token',
        value: token,
        domain: 'localhost',
        path: '/',
        secure: true,
        httpOnly: true,
        sameSite: 'Strict',
      }]);
      
      await page.goto(`${httpsInverseServer.baseUrl}/view`);
      
      // Wait for PDF to render
      await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 10000 });
      
      // Long-press on the PDF canvas to trigger inverse search (hold for 600ms)
      const canvas = page.locator('#viewer-container canvas').first();
      await canvas.hover();
      await canvas.dispatchEvent('mousedown');
      await page.waitForTimeout(600); // Wait longer than the 500ms threshold
      await canvas.dispatchEvent('mouseup');
      
      // Wait for tooltip to appear
      const tooltip = page.locator('.inverse-search-tooltip');
      await expect(tooltip).toBeVisible({ timeout: 5000 });
      
      // Press Escape key to cancel
      await page.keyboard.press('Escape');
      
      // Wait for tooltip to disappear
      await expect(tooltip).not.toBeVisible({ timeout: 5000 });
      
      // Verify no marker feedback is shown (tooltip was cancelled)
      const marker = page.locator('.synctex-marker');
      await expect(marker).not.toBeVisible({ timeout: 2000 });
    });

    test('ctrl+click shows inverse search tooltip with confirmation', async ({ page, httpsInverseServer }) => {
      // Load the PDF
      await fetch(`${httpsInverseServer.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': httpsInverseServer.apiKey,
        },
        body: JSON.stringify({
          pdf_path: EXAMPLE_PDF,
        }),
      });
      
      // Get auth token and set cookie
      const stateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
      const stateData = await stateResponse.json();
      const token = stateData.websocket_token;
      
      await page.context().addCookies([{
        name: 'pdf_token',
        value: token,
        domain: 'localhost',
        path: '/',
        secure: true,
        httpOnly: true,
        sameSite: 'Strict',
      }]);
      
      await page.goto(`${httpsInverseServer.baseUrl}/view`);
      
      // Wait for PDF to render
      await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 10000 });
      
      // Ctrl+Click on the PDF canvas to trigger inverse search
      // Use keyboard.down/up to properly simulate holding Ctrl during click
      const canvas = page.locator('#viewer-container canvas').first();
      await page.keyboard.down('Control');
      await canvas.click();
      await page.keyboard.up('Control');
      
      // Wait for tooltip to appear
      const tooltip = page.locator('.inverse-search-tooltip');
      await expect(tooltip).toBeVisible({ timeout: 5000 });
      
      // Verify tooltip content
      await expect(tooltip.locator('text=Go to Source?')).toBeVisible();
      await expect(tooltip.locator('button.tooltip-btn-confirm')).toContainText('Confirm (Enter)');
      
      // Click the confirm button
      await tooltip.locator('button.tooltip-btn-confirm').click();
      
      // Wait for tooltip to disappear
      await expect(tooltip).not.toBeVisible({ timeout: 5000 });
      
      // Verify red marker feedback is shown
      const marker = page.locator('.synctex-marker');
      await expect(marker).toBeVisible({ timeout: 5000 });
    });

    test('cmd+click (macOS) shows inverse search tooltip', async ({ page, httpsInverseServer }) => {
      // Load the PDF
      await fetch(`${httpsInverseServer.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': httpsInverseServer.apiKey,
        },
        body: JSON.stringify({
          pdf_path: EXAMPLE_PDF,
        }),
      });
      
      // Get auth token and set cookie
      const stateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
      const stateData = await stateResponse.json();
      const token = stateData.websocket_token;
      
      await page.context().addCookies([{
        name: 'pdf_token',
        value: token,
        domain: 'localhost',
        path: '/',
        secure: true,
        httpOnly: true,
        sameSite: 'Strict',
      }]);
      
      await page.goto(`${httpsInverseServer.baseUrl}/view`);
      
      // Wait for PDF to render
      await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 10000 });
      
      // Cmd+Click (metaKey) on the PDF canvas to trigger inverse search (macOS)
      // Use keyboard.down/up to properly simulate holding Cmd during click
      const canvas = page.locator('#viewer-container canvas').first();
      await page.keyboard.down('Meta');
      await canvas.click();
      await page.keyboard.up('Meta');
      
      // Wait for tooltip to appear
      const tooltip = page.locator('.inverse-search-tooltip');
      await expect(tooltip).toBeVisible({ timeout: 5000 });
      
      // Press Escape to dismiss
      await page.keyboard.press('Escape');
      await expect(tooltip).not.toBeVisible({ timeout: 5000 });
    });

    test('regular click does not show inverse search tooltip', async ({ page, httpsInverseServer }) => {
      // Load the PDF
      await fetch(`${httpsInverseServer.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': httpsInverseServer.apiKey,
        },
        body: JSON.stringify({
          pdf_path: EXAMPLE_PDF,
        }),
      });
      
      // Get auth token and set cookie
      const stateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
      const stateData = await stateResponse.json();
      const token = stateData.websocket_token;
      
      await page.context().addCookies([{
        name: 'pdf_token',
        value: token,
        domain: 'localhost',
        path: '/',
        secure: true,
        httpOnly: true,
        sameSite: 'Strict',
      }]);
      
      await page.goto(`${httpsInverseServer.baseUrl}/view`);
      
      // Wait for PDF to render
      await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 10000 });
      
      // Regular click (no modifier) on the PDF canvas
      const canvas = page.locator('#viewer-container canvas').first();
      await canvas.click();
      
      // Wait a moment to ensure no tooltip appears
      await page.waitForTimeout(500);
      
      // Tooltip should NOT be visible
      const tooltip = page.locator('.inverse-search-tooltip');
      await expect(tooltip).not.toBeVisible();
    });

    test('tooltip can be dismissed and re-shown', async ({ page, httpsInverseServer }) => {
      // Load the PDF
      await fetch(`${httpsInverseServer.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': httpsInverseServer.apiKey,
        },
        body: JSON.stringify({
          pdf_path: EXAMPLE_PDF,
        }),
      });
      
      // Get auth token and set cookie
      const stateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
      const stateData = await stateResponse.json();
      const token = stateData.websocket_token;
      
      await page.context().addCookies([{
        name: 'pdf_token',
        value: token,
        domain: 'localhost',
        path: '/',
        secure: true,
        httpOnly: true,
        sameSite: 'Strict',
      }]);
      
      await page.goto(`${httpsInverseServer.baseUrl}/view`);
      
      // Wait for PDF to render
      await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 10000 });
      
      // First long-press - show tooltip and dismiss by clicking outside
      const canvas = page.locator('#viewer-container canvas').first();
      await canvas.hover();
      await canvas.dispatchEvent('mousedown');
      await page.waitForTimeout(600);
      await canvas.dispatchEvent('mouseup');
      
      const tooltip = page.locator('.inverse-search-tooltip');
      await expect(tooltip).toBeVisible({ timeout: 5000 });
      
      // Dismiss by clicking outside the tooltip (on the PDF canvas)
      await canvas.click();
      await expect(tooltip).not.toBeVisible({ timeout: 5000 });
      
      // Wait a moment to ensure cleanup
      await page.waitForTimeout(500);
      
      // Second long-press - should work normally
      await canvas.hover();
      await canvas.dispatchEvent('mousedown');
      await page.waitForTimeout(600);
      await canvas.dispatchEvent('mouseup');
      await expect(tooltip).toBeVisible({ timeout: 5000 });
      
      // Click confirm button - should work (tooltip state was properly cleaned up)
      await tooltip.locator('button.tooltip-btn-confirm').click();
      await expect(tooltip).not.toBeVisible({ timeout: 5000 });
      
      // Verify red marker feedback is shown
      const marker = page.locator('.synctex-marker');
      await expect(marker).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('HTTPS without Inverse Search', () => {
    test('inverse search is disabled', async ({ httpsServer }) => {
      const response = await fetch(`${httpsServer.baseUrl}/state`);
      const data = await response.json();
      
      expect(data.inverse_search_enabled).toBeFalsy();
    });
  });

  test.describe('HTTP Mode (Inverse Search Disabled)', () => {
    test('inverse search is disabled in HTTP mode', async ({ httpServer }) => {
      const response = await fetch(`${httpServer.baseUrl}/state`);
      const data = await response.json();
      
      expect(data.inverse_search_enabled).toBeFalsy();
    });
  });
});
