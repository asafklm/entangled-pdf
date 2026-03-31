import { afterAll, beforeAll } from 'vitest';
import { startServer, type ServerInfo } from './fixtures/server';

declare module 'vitest' {
  interface TestContext {
    server: ServerInfo;
  }
}

let currentServer: ServerInfo | null = null;

/**
 * Start server before all tests in a file
 * 
 * Usage in test file:
 * ```typescript
 * import { setupServer, httpsServer } from './setup';
 * 
 * describe('my tests', () => {
 *   setupServer(httpsServer);
 *   
 *   it('test', async ({ server }) => {
 *     await page.goto(`${server.baseUrl}/view`);
 *   });
 * });
 * ```
 */
export function setupServer(options: Parameters<typeof startServer>[0] = {}) {
  beforeAll(async () => {
    currentServer = await startServer(options);
    return currentServer;
  });

  afterAll(async () => {
    if (currentServer) {
      await currentServer.stop();
      currentServer = null;
    }
  });
}

/**
 * Preset configurations for common server setups
 */
export const httpsServer = { https: true };
export const httpServer = { https: false };
export const httpsWithInverseSearch = { https: true, inverseSearch: true };
