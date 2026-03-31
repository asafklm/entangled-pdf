import { test, expect } from './fixtures';
import { join } from 'path';

const EXAMPLES_DIR = join(__dirname, '../../examples');
const EXAMPLE_PDF = join(EXAMPLES_DIR, 'example.pdf');

test.describe('PDF Viewer E2E', () => {

  test('shows "No PDF loaded" message when no PDF is configured', async ({ page, httpsServer }) => {
    await page.goto(`${httpsServer.baseUrl}/view`);
    
    await expect(page.getByText('No PDF loaded')).toBeVisible();
  });

  test('shows viewer container', async ({ page, httpsServer }) => {
    await page.goto(`${httpsServer.baseUrl}/view`);
    
    // The viewer container exists (may be hidden until PDF loads)
    const container = page.locator('#viewer-container');
    await expect(container).toBeAttached();
  });

  test('loads PDF via API and viewer displays it', async ({ page, httpsServer }) => {
    await page.goto(`${httpsServer.baseUrl}/view`);
    
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
  });

  test('returns error for invalid PDF path', async ({ httpsServer }) => {
    const response = await fetch(`${httpsServer.baseUrl}/api/load-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': httpsServer.apiKey,
      },
      body: JSON.stringify({
        pdf_path: '/nonexistent/path/to/file.pdf',
      }),
    });
    
    expect(response.ok).toBeFalsy();
  });

  test('state endpoint returns state information', async ({ httpsServer }) => {
    const response = await fetch(`${httpsServer.baseUrl}/state`);
    const data = await response.json();
    
    expect(data).toHaveProperty('pdf_loaded');
    expect(data).toHaveProperty('page');
  });
});
