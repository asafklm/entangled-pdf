import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { startServer, type ServerInfo } from './fixtures/server';

describe('PDF Viewer E2E', () => {
  let server: ServerInfo;

  beforeAll(async () => {
    server = await startServer({ https: true });
  });

  afterAll(async () => {
    await server.stop();
  });

  describe('Initial Load', () => {
    it('shows "No PDF loaded" message when no PDF is configured', async () => {
      const response = await fetch(`${server.baseUrl}/view`);
      const html = await response.text();
      
      expect(html).toContain('No PDF loaded');
    });

    it('shows viewer container', async () => {
      const response = await fetch(`${server.baseUrl}/view`);
      const html = await response.text();
      
      expect(html).toContain('viewer-container');
    });
  });

  describe('PDF Loading', () => {
    it('loads PDF via API and returns success', async () => {
      const examplePdf = new URL('../../../../examples/example.pdf', import.meta.url).pathname;
      const response = await fetch(`${server.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': server.apiKey,
        },
        body: JSON.stringify({
          pdf_path: examplePdf,
        }),
      });
      
      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.status).toBe('success');
    });

    it('returns error for invalid PDF path', async () => {
      const response = await fetch(`${server.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': server.apiKey,
        },
        body: JSON.stringify({
          pdf_path: '/nonexistent/path/to/file.pdf',
        }),
      });
      
      expect(response.ok).toBe(false);
    });
  });

  describe('State Endpoint', () => {
    it('returns state information', async () => {
      const response = await fetch(`${server.baseUrl}/state`);
      
      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data).toHaveProperty('pdf_loaded');
      expect(data).toHaveProperty('page');
    });
  });
});
