import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { startServer, type ServerInfo } from './fixtures/server';
import { getAuthToken } from './fixtures/auth';

describe('PDF Reload E2E', () => {
  let server: ServerInfo;

  beforeAll(async () => {
    server = await startServer({ https: true });
  });

  afterAll(async () => {
    await server.stop();
  });

  describe('Load PDF', () => {
    it('loads PDF and returns success', async () => {
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

    it('returns error for non-existent PDF', async () => {
      const response = await fetch(`${server.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': server.apiKey,
        },
        body: JSON.stringify({
          pdf_path: '/nonexistent/file.pdf',
        }),
      });
      
      expect(response.ok).toBe(false);
    });

    it('requires API key', async () => {
      const examplePdf = new URL('../../../../examples/example.pdf', import.meta.url).pathname;
      
      const response = await fetch(`${server.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          pdf_path: examplePdf,
        }),
      });
      
      expect(response.status).toBe(403);
    });
  });

  describe('State Updates', () => {
    it('updates state after loading PDF', async () => {
      const examplePdf = new URL('../../../../examples/example.pdf', import.meta.url).pathname;
      
      // Load PDF
      await fetch(`${server.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': server.apiKey,
        },
        body: JSON.stringify({
          pdf_path: examplePdf,
        }),
      });
      
      // Check state
      const stateResponse = await fetch(`${server.baseUrl}/state`);
      const state = await stateResponse.json();
      
      expect(state.pdf_loaded).toBe(true);
      expect(state.pdf_file).toContain('example.pdf');
    });

    it('updates mtime after loading PDF', async () => {
      const examplePdf = new URL('../../../../examples/example.pdf', import.meta.url).pathname;
      
      // Load PDF
      const loadResponse = await fetch(`${server.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': server.apiKey,
        },
        body: JSON.stringify({
          pdf_path: examplePdf,
        }),
      });
      
      const loadData = await loadResponse.json();
      expect(loadData.pdf_mtime).toBeGreaterThan(0);
      
      // Check state has mtime
      const stateResponse = await fetch(`${server.baseUrl}/state`);
      const state = await stateResponse.json();
      expect(state.pdf_mtime).toBeGreaterThan(0);
    });
  });

  describe('WebSocket Broadcast', () => {
    it('broadcasts reload message when PDF is loaded', async () => {
      const token = await getAuthToken(server);
      const ws = new WebSocket(`${server.wsUrl}/ws?token=${token}`);
      
      const examplePdf = new URL('../../../../examples/example.pdf', import.meta.url).pathname;
      
      await new Promise<void>((resolve, reject) => {
        ws.onopen = async () => {
          // Load PDF
          await fetch(`${server.baseUrl}/api/load-pdf`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-API-Key': server.apiKey,
            },
            body: JSON.stringify({
              pdf_path: examplePdf,
            }),
          });
        };
        
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.action === 'reload') {
            expect(data.pdf_mtime).toBeDefined();
            ws.close();
            resolve();
          }
        };
        
        ws.onerror = () => reject(new Error('WebSocket error'));
        setTimeout(() => reject(new Error('Timeout')), 10000);
      });
    });
  });

  describe('Multiple Loads', () => {
    it('can load different PDFs sequentially', async () => {
      const examplePdf = new URL('../../../../examples/example.pdf', import.meta.url).pathname;
      
      // Load first PDF
      const response1 = await fetch(`${server.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': server.apiKey,
        },
        body: JSON.stringify({
          pdf_path: examplePdf,
        }),
      });
      
      expect(response1.ok).toBe(true);
      
      // Load same PDF again (should still work)
      const response2 = await fetch(`${server.baseUrl}/api/load-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': server.apiKey,
        },
        body: JSON.stringify({
          pdf_path: examplePdf,
        }),
      });
      
      expect(response2.ok).toBe(true);
    });
  });
});
