import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { startServer, type ServerInfo } from './fixtures/server';
import { gotoWithAuth, getAuthToken } from './fixtures/auth';

describe('WebSocket E2E', () => {
  let server: ServerInfo;

  beforeAll(async () => {
    server = await startServer({ https: true });
  });

  afterAll(async () => {
    await server.stop();
  });

  describe('Connection Lifecycle', () => {
    it('WebSocket endpoint is available', async () => {
      const token = await getAuthToken(server);
      expect(token).not.toBeNull();
    });

    it('WebSocket accepts connection with valid token', async () => {
      const token = await getAuthToken(server);
      
      // Create WebSocket connection
      const ws = new WebSocket(`${server.wsUrl}/ws?token=${token}`);
      
      await new Promise<void>((resolve, reject) => {
        ws.onopen = () => {
          ws.close();
          resolve();
        };
        ws.onerror = (err) => {
          reject(new Error('WebSocket connection failed'));
        };
      });
    });

    it('WebSocket rejects connection without token', async () => {
      const ws = new WebSocket(`${server.wsUrl}/ws`);
      
      await new Promise<void>((resolve) => {
        ws.onclose = (event) => {
          // Should close with error code
          expect(event.code).toBeGreaterThan(1000);
          resolve();
        };
        ws.onerror = () => {
          // Error is expected
        };
      });
    });

    it('WebSocket receives broadcast messages', async () => {
      const token = await getAuthToken(server);
      const ws = new WebSocket(`${server.wsUrl}/ws?token=${token}`);
      
      await new Promise<void>((resolve, reject) => {
        ws.onopen = async () => {
          // Load a PDF to trigger broadcast
          const examplePdf = new URL('../../../../examples/example.pdf', import.meta.url).pathname;
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
            ws.close();
            resolve();
          }
        };
        
        ws.onerror = () => {
          reject(new Error('WebSocket error'));
        };
        
        // Timeout after 10 seconds
        setTimeout(() => {
          reject(new Error('Timeout waiting for message'));
        }, 10000);
      });
    });
  });

  describe('Message Handling', () => {
    it('WebSocket receives synctex messages', async () => {
      const token = await getAuthToken(server);
      const ws = new WebSocket(`${server.wsUrl}/ws?token=${token}`);
      
      // Load PDF first
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
          
          // Wait for reload message
          ws.onmessage = async (event) => {
            const data = JSON.parse(event.data);
            if (data.action === 'reload') {
              // Now send synctex forward search
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
              expect(data.page).toBeDefined();
              expect(data.x).toBeDefined();
              expect(data.y).toBeDefined();
              ws.close();
              resolve();
            }
          };
        };
        
        ws.onerror = () => {
          reject(new Error('WebSocket error'));
        };
        
        setTimeout(() => {
          reject(new Error('Timeout'));
        }, 15000);
      });
    });
  });
});
