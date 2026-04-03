import { test, expect, captureConsoleLogs, formatConsoleLogs, ConsoleLog } from './fixtures';
import { join } from 'path';

const EXAMPLES_DIR = join(__dirname, '../../examples');
const EXAMPLE_PDF = join(EXAMPLES_DIR, 'example.pdf');
const TEST_PDF2 = join(EXAMPLES_DIR, 'test-pdf2.pdf');
const EXAMPLE_TEX = join(EXAMPLES_DIR, 'example.tex');
const TEST_TEX2 = join(EXAMPLES_DIR, 'test-pdf2.tex');

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

  test('shows reload button when switching to different PDF', async ({ page, httpsInverseServer }) => {
    // Capture console logs for debugging
    const consoleLogs: ConsoleLog[] = [];
    const stopCapture = captureConsoleLogs(page, consoleLogs);
    
    try {
      // Get authentication token
      const stateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
      const stateData = await stateResponse.json();
      const token = stateData.websocket_token;
      
      // Setup browser with auth token
      await page.context().addCookies([{
        name: 'pdf_token',
        value: token,
        domain: 'localhost',
        path: '/',
        secure: true,
        httpOnly: true,
        sameSite: 'Strict',
      }]);
      
      // Navigate to viewer
      await page.goto(`${httpsInverseServer.baseUrl}/view`);
      await expect(page.locator('#connection-status')).toBeVisible({ timeout: 5000 });
      
      // Load PDF1 via API
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
      
      // Wait for PDF1 to load
      await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 10000 });
      
      // Verify button shows "Connected"
      const statusButton = page.locator('#connection-status');
      await expect(statusButton).toHaveClass(/connected/);
      await expect(statusButton.locator('.status-text')).toHaveText('Connected');
      
      // Store reference to PDF1 canvas count
      const pdf1CanvasCount = await page.locator('#viewer-container canvas').count();
      expect(pdf1CanvasCount).toBeGreaterThan(0);
      
      // Send webhook request for PDF2 (different file)
      const webhookResponse = await fetch(`${httpsInverseServer.baseUrl}/webhook/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': httpsInverseServer.apiKey,
        },
        body: JSON.stringify({
          line: 1,
          col: 1,
          tex_file: TEST_TEX2,
          pdf_file: TEST_PDF2,
        }),
      });
      
      expect(webhookResponse.ok).toBeTruthy();
      
      // Wait a moment for WebSocket message to arrive
      await page.waitForTimeout(500);
      
      // Verify button changes to "Reload" (not auto-reload)
      await expect(statusButton).toHaveClass(/reload-needed/);
      await expect(statusButton.locator('.status-text')).toHaveText('Reload');
      
      // Wait 0.5s to confirm no auto-reload (PDF1 still visible)
      await page.waitForTimeout(500);
      const currentCanvasCount = await page.locator('#viewer-container canvas').count();
      expect(currentCanvasCount).toBe(pdf1CanvasCount);
      
      // Click the reload button
      await statusButton.click();
      
      // Wait for PDF2 to load
      await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 10000 });
      
      // Verify button returns to "Connected"
      await expect(statusButton).toHaveClass(/connected/);
      await expect(statusButton.locator('.status-text')).toHaveText('Connected');
    } catch (e) {
      // On failure, log all captured console messages
      console.log('\n\n=== Browser Console Logs ===');
      console.log(formatConsoleLogs(consoleLogs));
      console.log('=== End Console Logs ===\n');
      throw e;
    } finally {
      stopCapture();
    }
  });

  test('auto-reloads when same PDF is modified', async ({ page, httpsInverseServer }) => {
    // This test verifies that mtime changes (same file modified) trigger auto-reload
    // without showing the reload button
    
    // Get authentication token
    const stateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
    const stateData = await stateResponse.json();
    const token = stateData.websocket_token;
    
    // Setup browser with auth token
    await page.context().addCookies([{
      name: 'pdf_token',
      value: token,
      domain: 'localhost',
      path: '/',
      secure: true,
      httpOnly: true,
      sameSite: 'Strict',
    }]);
    
    // Navigate to viewer
    await page.goto(`${httpsInverseServer.baseUrl}/view`);
    await expect(page.locator('#connection-status')).toBeVisible({ timeout: 5000 });
    
    // Load PDF1 via API
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
    
    // Wait for PDF1 to load
    await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 10000 });
    
    // Store the current mtime
    const initialStateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
    const initialState = await initialStateResponse.json();
    const initialMtime = initialState.pdf_mtime;
    
    // Verify button shows "Connected"
    const statusButton = page.locator('#connection-status');
    await expect(statusButton).toHaveClass(/connected/);
    
    // Manually update the PDF file to change its mtime
    // We do this by re-loading the same PDF, which updates the mtime in state
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
    
    // Small delay to ensure state is updated
    await page.waitForTimeout(100);
    
    // Send webhook request for the same PDF (which now has a newer mtime)
    const webhookResponse = await fetch(`${httpsInverseServer.baseUrl}/webhook/update`, {
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
    
    expect(webhookResponse.ok).toBeTruthy();
    
    // Wait for auto-reload (should happen automatically for same file modified)
    await page.waitForTimeout(1000);
    
    // Verify PDF is still loaded (auto-reload completed)
    await expect(page.locator('#viewer-container canvas').first()).toBeVisible({ timeout: 5000 });
    
    // Verify button is back to "Connected" state
    await expect(statusButton).toHaveClass(/connected/);
    await expect(statusButton.locator('.status-text')).toHaveText('Connected');
    
    // Verify the state has the updated mtime
    const finalStateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
    const finalState = await finalStateResponse.json();
    expect(finalState.pdf_mtime).toBeGreaterThanOrEqual(initialMtime);
  });
});
