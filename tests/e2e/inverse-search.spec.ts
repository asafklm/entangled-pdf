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
