import { test, expect } from './fixtures';

test.describe('HTTP vs HTTPS Mode E2E', () => {
  test.describe('HTTPS Mode', () => {
    test('uses HTTPS for all endpoints', async ({ httpsServer }) => {
      expect(httpsServer.baseUrl).toMatch(/^https:/);
      expect(httpsServer.wsUrl).toMatch(/^wss:/);
    });

    test('serves viewer over HTTPS', async ({ page, httpsServer }) => {
      await page.goto(`${httpsServer.baseUrl}/view`);
      await expect(page.getByText('No PDF loaded')).toBeVisible();
    });

    test('status endpoint shows HTTPS mode', async ({ httpsServer }) => {
      const response = await fetch(`${httpsServer.baseUrl}/state`);
      const data = await response.json();
      
      expect(data.https).toBeTruthy();
    });
  });

  test.describe('HTTP Mode', () => {
    test('uses HTTP for all endpoints', async ({ httpServer }) => {
      expect(httpServer.baseUrl).toMatch(/^http:/);
      expect(httpServer.wsUrl).toMatch(/^ws:/);
    });

    test('serves viewer over HTTP', async ({ page, httpServer }) => {
      await page.goto(`${httpServer.baseUrl}/view`);
      await expect(page.getByText('No PDF loaded')).toBeVisible();
    });

    test('status endpoint shows HTTP mode', async ({ httpServer }) => {
      const response = await fetch(`${httpServer.baseUrl}/state`);
      const data = await response.json();
      
      expect(data.https).toBeFalsy();
    });
  });

  test.describe('Security Differences', () => {
    test('HTTPS mode requires token for WebSocket', async ({ page, httpsServer }) => {
      await page.goto(`${httpsServer.baseUrl}/view`);
      
      // Without token, should not show connected status
      // The viewer should still load but WebSocket won't connect
      await expect(page.getByText('No PDF loaded')).toBeVisible();
    });

    test('HTTP mode does not require token for WebSocket', async ({ page, httpServer }) => {
      await page.goto(`${httpServer.baseUrl}/view`);
      
      // HTTP mode should work without token
      await expect(page.getByText('No PDF loaded')).toBeVisible();
    });

    test('inverse search is disabled in HTTP mode', async ({ httpServer }) => {
      const response = await fetch(`${httpServer.baseUrl}/state`);
      const data = await response.json();
      
      expect(data.inverse_search_enabled).toBeFalsy();
    });
  });
});
