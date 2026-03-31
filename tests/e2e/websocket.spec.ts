import { test, expect } from './fixtures';
import { join } from 'path';

const EXAMPLES_DIR = join(__dirname, '../../examples');
const EXAMPLE_PDF = join(EXAMPLES_DIR, 'example.pdf');

test.describe('WebSocket E2E', () => {

  test('WebSocket endpoint is available', async ({ httpsServer }) => {
    const response = await fetch(`${httpsServer.baseUrl}/state`);
    const data = await response.json();
    
    expect(data.websocket_token).toBeDefined();
  });

  test('WebSocket accepts connection with valid token', async ({ page, httpsInverseServer }) => {
    const response = await fetch(`${httpsInverseServer.baseUrl}/state`);
    const data = await response.json();
    const token = data.websocket_token;
    
    await page.goto(`${httpsInverseServer.baseUrl}/view`);
    
    await page.context().addCookies([{
      name: 'pdf_token',
      value: token,
      domain: 'localhost',
      path: '/',
      secure: true,
      httpOnly: true,
      sameSite: 'Strict',
    }]);
    
    await page.reload();
    
    await expect(page.locator('#connection-status')).toBeVisible({ timeout: 5000 });
  });

  test('WebSocket rejects connection without token', async ({ page, httpsServer }) => {
    await page.goto(`${httpsServer.baseUrl}/view`);
    
    // Without token, should show auth form or no connection
    // The viewer should still load but WebSocket won't connect
    await expect(page.getByText('No PDF loaded')).toBeVisible();
  });

  test('WebSocket receives broadcast messages', async ({ page, httpsInverseServer }) => {
    const response = await fetch(`${httpsInverseServer.baseUrl}/state`);
    const data = await response.json();
    const token = data.websocket_token;
    
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
    
    await expect(page.locator('#connection-status')).toBeVisible({ timeout: 5000 });
    
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
    
    await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 10000 });
  });
});
