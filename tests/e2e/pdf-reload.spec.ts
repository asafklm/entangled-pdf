import { test, expect } from './fixtures';
import { join } from 'path';

const EXAMPLES_DIR = join(__dirname, '../../examples');
const EXAMPLE_PDF = join(EXAMPLES_DIR, 'example.pdf');

test.describe('PDF Reload E2E', () => {
  test('loads PDF and returns success', async ({ httpsServer }) => {
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
    const data = await response.json();
    expect(data.status).toBe('success');
  });

  test('returns error for non-existent PDF', async ({ httpsServer }) => {
    const response = await fetch(`${httpsServer.baseUrl}/api/load-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': httpsServer.apiKey,
      },
      body: JSON.stringify({
        pdf_path: '/nonexistent/file.pdf',
      }),
    });
    
    expect(response.ok).toBeFalsy();
  });

  test('requires API key', async ({ httpsServer }) => {
    const response = await fetch(`${httpsServer.baseUrl}/api/load-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        pdf_path: EXAMPLE_PDF,
      }),
    });
    
    expect(response.status).toBe(403);
  });

  test('updates state after loading PDF', async ({ httpsServer }) => {
    await fetch(`${httpsServer.baseUrl}/api/load-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': httpsServer.apiKey,
      },
      body: JSON.stringify({
        pdf_path: EXAMPLE_PDF,
      }),
    });
    
    const stateResponse = await fetch(`${httpsServer.baseUrl}/state`);
    const state = await stateResponse.json();
    
    expect(state.pdf_loaded).toBeTruthy();
    expect(state.pdf_file).toContain('example.pdf');
  });

  test('broadcasts reload message when PDF is loaded', async ({ page, httpsInverseServer }) => {
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
