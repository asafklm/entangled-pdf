import { test, expect } from './fixtures';
import { join } from 'path';

const EXAMPLES_DIR = join(__dirname, '../../examples');
const EXAMPLE_PDF = join(EXAMPLES_DIR, 'example.pdf');

test.describe('Multi-Tab Broadcast E2E', () => {
  test('multiple clients can connect simultaneously', async ({ context, httpsInverseServer }) => {
    const stateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
    const stateData = await stateResponse.json();
    const token = stateData.websocket_token;
    
    await context.addCookies([{
      name: 'pdf_token',
      value: token,
      domain: 'localhost',
      path: '/',
      secure: true,
      httpOnly: true,
      sameSite: 'Strict',
    }]);
    
    const page1 = await context.newPage();
    const page2 = await context.newPage();
    
    await page1.goto(`${httpsInverseServer.baseUrl}/view`);
    await page2.goto(`${httpsInverseServer.baseUrl}/view`);
    
    await expect(page1.locator('#connection-status')).toBeVisible({ timeout: 5000 });
    await expect(page2.locator('#connection-status')).toBeVisible({ timeout: 5000 });
    
    await page1.close();
    await page2.close();
  });

  test('broadcast reaches all connected clients', async ({ context, httpsInverseServer }) => {
    const stateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
    const stateData = await stateResponse.json();
    const token = stateData.websocket_token;
    
    await context.addCookies([{
      name: 'pdf_token',
      value: token,
      domain: 'localhost',
      path: '/',
      secure: true,
      httpOnly: true,
      sameSite: 'Strict',
    }]);
    
    const page1 = await context.newPage();
    const page2 = await context.newPage();
    
    await page1.goto(`${httpsInverseServer.baseUrl}/view`);
    await page2.goto(`${httpsInverseServer.baseUrl}/view`);
    
    await expect(page1.locator('#connection-status')).toBeVisible({ timeout: 5000 });
    await expect(page2.locator('#connection-status')).toBeVisible({ timeout: 5000 });
    
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
    
    await expect(page1.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 10000 });
    await expect(page2.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 10000 });
    
    await page1.close();
    await page2.close();
  });
});
