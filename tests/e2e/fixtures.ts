import { test as base, expect } from '@playwright/test';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const PROJECT_ROOT = join(__dirname, '..', '..');
const SERVER_INFO_FILE = join(PROJECT_ROOT, '.test-servers.json');

export interface ServerInfo {
  port: number;
  baseUrl: string;
  wsUrl: string;
  apiKey: string;
}

function getServerInfo(): { httpsPort: number; httpPort: number; httpsInversePort: number; apiKey: string } {
  if (!existsSync(SERVER_INFO_FILE)) {
    throw new Error('Server info file not found. Make sure global setup ran.');
  }
  return JSON.parse(readFileSync(SERVER_INFO_FILE, 'utf-8'));
}

async function resetServerState(baseUrl: string, apiKey: string): Promise<void> {
  try {
    await fetch(`${baseUrl}/api/test/reset`, {
      method: 'POST',
      headers: {
        'X-API-Key': apiKey,
      },
    });
  } catch {
    // Ignore errors - reset endpoint may not exist in all server modes
  }
}

export const test = base.extend<{
  httpsServer: ServerInfo;
  httpServer: ServerInfo;
  httpsInverseServer: ServerInfo;
}>({
  httpsServer: async ({}, use) => {
    const info = getServerInfo();
    const serverInfo: ServerInfo = {
      port: info.httpsPort,
      baseUrl: `https://localhost:${info.httpsPort}`,
      wsUrl: `wss://localhost:${info.httpsPort}`,
      apiKey: info.apiKey,
    };
    await resetServerState(serverInfo.baseUrl, serverInfo.apiKey);
    await use(serverInfo);
  },
  
  httpServer: async ({}, use) => {
    const info = getServerInfo();
    const serverInfo: ServerInfo = {
      port: info.httpPort,
      baseUrl: `http://localhost:${info.httpPort}`,
      wsUrl: `ws://localhost:${info.httpPort}`,
      apiKey: info.apiKey,
    };
    await resetServerState(serverInfo.baseUrl, serverInfo.apiKey);
    await use(serverInfo);
  },
  
  httpsInverseServer: async ({}, use) => {
    const info = getServerInfo();
    const serverInfo: ServerInfo = {
      port: info.httpsInversePort,
      baseUrl: `https://localhost:${info.httpsInversePort}`,
      wsUrl: `wss://localhost:${info.httpsInversePort}`,
      apiKey: info.apiKey,
    };
    await resetServerState(serverInfo.baseUrl, serverInfo.apiKey);
    await use(serverInfo);
  },
});

export { expect };
