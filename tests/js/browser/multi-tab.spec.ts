import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { startServer, type ServerInfo } from './fixtures/server';
import { getAuthToken } from './fixtures/auth';

describe('Multi-Tab Broadcast E2E', () => {
  let server: ServerInfo;

  beforeAll(async () => {
    server = await startServer({ https: true });
  });

  afterAll(async () => {
    await server.stop();
  });

  describe('Multiple WebSocket Connections', () => {
    it('multiple clients can connect simultaneously', async () => {
      const token = await getAuthToken(server);
      
      const ws1 = new WebSocket(`${server.wsUrl}/ws?token=${token}`);
      const ws2 = new WebSocket(`${server.wsUrl}/ws?token=${token}`);
      
      await Promise.all([
        new Promise<void>((resolve) => {
          ws1.onopen = () => resolve();
        }),
        new Promise<void>((resolve) => {
          ws2.onopen = () => resolve();
        }),
      ]);
      
      ws1.close();
      ws2.close();
    });

    it('broadcast reaches all connected clients', async () => {
      const token = await getAuthToken(server);
      const examplePdf = new URL('../../../../examples/example.pdf', import.meta.url).pathname;
      
      const ws1 = new WebSocket(`${server.wsUrl}/ws?token=${token}`);
      const ws2 = new WebSocket(`${server.wsUrl}/ws?token=${token}`);
      
      let ws1Received = false;
      let ws2Received = false;
      
      await new Promise<void>((resolve, reject) => {
        let connectionsReady = 0;
        
        const checkReady = () => {
          connectionsReady++;
          if (connectionsReady === 2) {
            // Both connected, load PDF to trigger broadcast
            fetch(`${server.baseUrl}/api/load-pdf`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-API-Key': server.apiKey,
              },
              body: JSON.stringify({
                pdf_path: examplePdf,
              }),
            });
          }
        };
        
        ws1.onopen = checkReady;
        ws2.onopen = checkReady;
        
        ws1.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.action === 'reload') {
            ws1Received = true;
            if (ws1Received && ws2Received) {
              ws1.close();
              ws2.close();
              resolve();
            }
          }
        };
        
        ws2.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.action === 'reload') {
            ws2Received = true;
            if (ws1Received && ws2Received) {
              ws1.close();
              ws2.close();
              resolve();
            }
          }
        };
        
        ws1.onerror = () => reject(new Error('WS1 error'));
        ws2.onerror = () => reject(new Error('WS2 error'));
        
        setTimeout(() => reject(new Error('Timeout')), 15000);
      });
      
      expect(ws1Received).toBe(true);
      expect(ws2Received).toBe(true);
    });

    it('disconnecting one client does not affect others', async () => {
      const token = await getAuthToken(server);
      const examplePdf = new URL('../../../../examples/example.pdf', import.meta.url).pathname;
      
      const ws1 = new WebSocket(`${server.wsUrl}/ws?token=${token}`);
      const ws2 = new WebSocket(`${server.wsUrl}/ws?token=${token}`);
      
      await new Promise<void>((resolve, reject) => {
        let connectionsReady = 0;
        
        ws1.onopen = () => {
          connectionsReady++;
          if (connectionsReady === 2) {
            // Disconnect ws1
            ws1.close();
            
            // Wait a bit, then load PDF
            setTimeout(() => {
              fetch(`${server.baseUrl}/api/load-pdf`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-API-Key': server.apiKey,
                },
                body: JSON.stringify({
                  pdf_path: examplePdf,
                }),
              });
            }, 100);
          }
        };
        
        ws2.onopen = () => {
          connectionsReady++;
          if (connectionsReady === 2) {
            ws1.close();
            setTimeout(() => {
              fetch(`${server.baseUrl}/api/load-pdf`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-API-Key': server.apiKey,
                },
                body: JSON.stringify({
                  pdf_path: examplePdf,
                }),
              });
            }, 100);
          }
        };
        
        ws2.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.action === 'reload') {
            ws2.close();
            resolve();
          }
        };
        
        ws1.onerror = () => {};
        ws2.onerror = () => reject(new Error('WS2 error'));
        
        setTimeout(() => reject(new Error('Timeout')), 15000);
      });
    });
  });
});
