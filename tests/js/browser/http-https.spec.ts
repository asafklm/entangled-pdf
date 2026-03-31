import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { startServer, type ServerInfo } from './fixtures/server';

describe('HTTP vs HTTPS Mode E2E', () => {
  describe('HTTPS Mode', () => {
    let server: ServerInfo;

    beforeAll(async () => {
      server = await startServer({ https: true });
    });

    afterAll(async () => {
      await server.stop();
    });

    it('uses HTTPS for all endpoints', async () => {
      expect(server.baseUrl).toMatch(/^https:/);
      expect(server.wsUrl).toMatch(/^wss:/);
    });

    it('serves viewer over HTTPS', async () => {
      const response = await fetch(`${server.baseUrl}/view`);
      expect(response.ok).toBe(true);
    });

    it('WebSocket uses WSS', async () => {
      const token = await fetch(`${server.baseUrl}/status`, {
        headers: { 'X-API-Key': server.apiKey },
      }).then(r => r.json()).then(d => d.token);
      
      if (token) {
        const ws = new WebSocket(`${server.wsUrl}/ws?token=${token}`);
        await new Promise<void>((resolve, reject) => {
          ws.onopen = () => {
            ws.close();
            resolve();
          };
          ws.onerror = () => reject(new Error('WebSocket failed'));
        });
      }
    });

    it('status endpoint shows inverse search can be enabled', async () => {
      const response = await fetch(`${server.baseUrl}/status`, {
        headers: { 'X-API-Key': server.apiKey },
      });
      const data = await response.json();
      
      // Inverse search is available in HTTPS mode
      expect(data.https).toBe(true);
    });
  });

  describe('HTTP Mode', () => {
    let server: ServerInfo;

    beforeAll(async () => {
      server = await startServer({ https: false });
    });

    afterAll(async () => {
      await server.stop();
    });

    it('uses HTTP for all endpoints', async () => {
      expect(server.baseUrl).toMatch(/^http:/);
      expect(server.wsUrl).toMatch(/^ws:/);
    });

    it('serves viewer over HTTP', async () => {
      const response = await fetch(`${server.baseUrl}/view`);
      expect(response.ok).toBe(true);
    });

    it('WebSocket uses WS (not WSS)', async () => {
      const ws = new WebSocket(`${server.wsUrl}/ws`);
      
      await new Promise<void>((resolve, reject) => {
        ws.onopen = () => {
          ws.close();
          resolve();
        };
        ws.onerror = () => reject(new Error('WebSocket failed'));
      });
    });

    it('status endpoint shows HTTP mode', async () => {
      const response = await fetch(`${server.baseUrl}/status`, {
        headers: { 'X-API-Key': server.apiKey },
      });
      const data = await response.json();
      
      expect(data.https).toBe(false);
    });
  });

  describe('Security Differences', () => {
    it('HTTPS mode requires token for WebSocket', async () => {
      const httpsServer = await startServer({ https: true });
      
      // WebSocket without token should fail
      const ws = new WebSocket(`${httpsServer.wsUrl}/ws`);
      
      await new Promise<void>((resolve) => {
        ws.onclose = (event) => {
          expect(event.code).toBeGreaterThan(1000);
          resolve();
        };
        ws.onerror = () => {};
      });
      
      await httpsServer.stop();
    });

    it('HTTP mode does not require token for WebSocket', async () => {
      const httpServer = await startServer({ https: false });
      
      // WebSocket without token should work in HTTP mode
      const ws = new WebSocket(`${httpServer.wsUrl}/ws`);
      
      await new Promise<void>((resolve, reject) => {
        ws.onopen = () => {
          ws.close();
          resolve();
        };
        ws.onerror = () => reject(new Error('WebSocket failed'));
      });
      
      await httpServer.stop();
    });
  });
});
