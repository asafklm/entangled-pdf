import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { startServer, type ServerInfo } from './fixtures/server';
import { getAuthToken } from './fixtures/auth';

describe('Forward Search E2E', () => {
  let server: ServerInfo;

  beforeAll(async () => {
    server = await startServer({ https: true });
  });

  afterAll(async () => {
    await server.stop();
  });

  describe('Webhook Endpoint', () => {
    it('webhook accepts synctex forward search request', async () => {
      const examplePdf = new URL('../../../../examples/example.pdf', import.meta.url).pathname;
      const exampleTex = new URL('../../../../examples/example.tex', import.meta.url).pathname;
      
      // Load PDF first
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
      
      // Send forward search request
      const response = await fetch(`${server.baseUrl}/webhook/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': server.apiKey,
        },
        body: JSON.stringify({
          line: 1,
          col: 1,
          tex_file: exampleTex,
          pdf_file: examplePdf,
        }),
      });
      
      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.status).toBe('success');
      expect(data.page).toBeDefined();
    });

    it('webhook returns error for invalid synctex params', async () => {
      const response = await fetch(`${server.baseUrl}/webhook/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': server.apiKey,
        },
        body: JSON.stringify({
          line: 1,
          // Missing col, tex_file, pdf_file
        }),
      });
      
      expect(response.ok).toBe(false);
    });

    it('webhook requires API key', async () => {
      const examplePdf = new URL('../../../../examples/example.pdf', import.meta.url).pathname;
      const exampleTex = new URL('../../../../examples/example.tex', import.meta.url).pathname;
      
      const response = await fetch(`${server.baseUrl}/webhook/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          line: 1,
          col: 1,
          tex_file: exampleTex,
          pdf_file: examplePdf,
        }),
      });
      
      expect(response.status).toBe(403);
    });
  });

  describe('WebSocket Broadcast', () => {
    it('forward search broadcasts synctex message via WebSocket', async () => {
      const token = await getAuthToken(server);
      const ws = new WebSocket(`${server.wsUrl}/ws?token=${token}`);
      
      const examplePdf = new URL('../../../../examples/example.pdf', import.meta.url).pathname;
      const exampleTex = new URL('../../../../examples/example.tex', import.meta.url).pathname;
      
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
        
        ws.onmessage = async (event) => {
          const data = JSON.parse(event.data);
          
          if (data.action === 'reload') {
            // PDF loaded, now send forward search
            await fetch(`${server.baseUrl}/webhook/update`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-API-Key': server.apiKey,
              },
              body: JSON.stringify({
                line: 1,
                col: 1,
                tex_file: exampleTex,
                pdf_file: examplePdf,
              }),
            });
          } else if (data.action === 'synctex') {
            // Verify synctex message structure
            expect(data.page).toBeGreaterThanOrEqual(1);
            expect(data.x).toBeDefined();
            expect(data.y).toBeDefined();
            expect(data.last_sync_time).toBeDefined();
            ws.close();
            resolve();
          }
        };
        
        ws.onerror = () => reject(new Error('WebSocket error'));
        setTimeout(() => reject(new Error('Timeout')), 15000);
      });
    });
  });

  describe('State Updates', () => {
    it('forward search updates server state', async () => {
      const examplePdf = new URL('../../../../examples/example.pdf', import.meta.url).pathname;
      const exampleTex = new URL('../../../../examples/example.tex', import.meta.url).pathname;
      
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
      
      // Send forward search
      await fetch(`${server.baseUrl}/webhook/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': server.apiKey,
        },
        body: JSON.stringify({
          line: 1,
          col: 1,
          tex_file: exampleTex,
          pdf_file: examplePdf,
        }),
      });
      
      // Check state endpoint
      const stateResponse = await fetch(`${server.baseUrl}/state`);
      const state = await stateResponse.json();
      
      expect(state.page).toBeGreaterThanOrEqual(1);
      expect(state.last_sync_time).toBeGreaterThan(0);
    });
  });
});
