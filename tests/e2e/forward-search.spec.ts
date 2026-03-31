import { test, expect } from './fixtures';
import { join } from 'path';

const EXAMPLES_DIR = join(__dirname, '../../examples');
const EXAMPLE_PDF = join(EXAMPLES_DIR, 'example.pdf');
const EXAMPLE_TEX = join(EXAMPLES_DIR, 'example.tex');

test.describe('Forward Search E2E', () => {

  test('webhook accepts synctex forward search request', async ({ httpsServer }) => {
    // Load PDF first
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
    
    // Send forward search request
    const response = await fetch(`${httpsServer.baseUrl}/webhook/update`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': httpsServer.apiKey,
      },
      body: JSON.stringify({
        line: 1,
        col: 1,
        tex_file: EXAMPLE_TEX,
        pdf_file: EXAMPLE_PDF,
      }),
    });
    
    expect(response.ok).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('success');
    expect(data.page).toBeDefined();
  });

  test('webhook returns error for invalid synctex params', async ({ httpsServer }) => {
    const response = await fetch(`${httpsServer.baseUrl}/webhook/update`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': httpsServer.apiKey,
      },
      body: JSON.stringify({
        line: 1,
        // Missing col, tex_file, pdf_file
      }),
    });
    
    expect(response.ok).toBeFalsy();
  });

  test('webhook requires API key', async ({ httpsServer }) => {
    const response = await fetch(`${httpsServer.baseUrl}/webhook/update`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        line: 1,
        col: 1,
        tex_file: EXAMPLE_TEX,
        pdf_file: EXAMPLE_PDF,
      }),
    });
    
    expect(response.status).toBe(403);
  });

  test('forward search broadcasts synctex message via WebSocket', async ({ page, httpsInverseServer }) => {
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
    
    await fetch(`${httpsInverseServer.baseUrl}/webhook/update`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': httpsInverseServer.apiKey,
      },
      body: JSON.stringify({
        line: 1,
        col: 1,
        tex_file: EXAMPLE_TEX,
        pdf_file: EXAMPLE_PDF,
      }),
    });
    
    await expect(page.locator('.synctex-marker')).toBeVisible({ timeout: 5000 });
  });

  test('forward search updates server state', async ({ httpsServer }) => {
    // Load PDF
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
    
    // Send forward search
    await fetch(`${httpsServer.baseUrl}/webhook/update`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': httpsServer.apiKey,
      },
      body: JSON.stringify({
        line: 1,
        col: 1,
        tex_file: EXAMPLE_TEX,
        pdf_file: EXAMPLE_PDF,
      }),
    });
    
    // Check state endpoint
    const stateResponse = await fetch(`${httpsServer.baseUrl}/state`);
    const state = await stateResponse.json();
    
    expect(state.page).toBeGreaterThanOrEqual(1);
    expect(state.last_sync_time).toBeGreaterThan(0);
  });
});
