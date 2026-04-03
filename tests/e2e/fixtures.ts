import { test as base, expect, ConsoleMessage } from '@playwright/test';
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

// Store console logs during tests
export interface ConsoleLog {
  type: string;
  text: string;
  location?: string;
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

// Helper function to attach console logs to test
export function captureConsoleLogs(page: any, logs: ConsoleLog[]): () => ConsoleLog[] {
  const consoleHandler = (msg: ConsoleMessage) => {
    const logEntry: ConsoleLog = {
      type: msg.type(),
      text: msg.text(),
    };
    
    // Add location if available
    const location = msg.location();
    if (location) {
      logEntry.location = `${location.url}:${location.lineNumber}:${location.columnNumber}`;
    }
    
    logs.push(logEntry);
    
    // Also output to test runner console for debugging
    const prefix = `[Browser Console ${msg.type()}]`;
    if (msg.type() === 'error') {
      console.error(prefix, msg.text());
    } else if (msg.type() === 'warning') {
      console.warn(prefix, msg.text());
    } else {
      console.log(prefix, msg.text());
    }
  };
  
  page.on('console', consoleHandler);
  
  // Also capture page errors
  const pageErrorHandler = (error: Error) => {
    const logEntry: ConsoleLog = {
      type: 'pageerror',
      text: error.message,
    };
    logs.push(logEntry);
    console.error('[Browser Page Error]', error.message);
  };
  
  page.on('pageerror', pageErrorHandler);
  
  // Return function to stop capturing and get logs
  return () => {
    page.off('console', consoleHandler);
    page.off('pageerror', pageErrorHandler);
    return logs;
  };
}

// Helper to format and display console logs
export function formatConsoleLogs(logs: ConsoleLog[]): string {
  if (logs.length === 0) {
    return 'No console logs captured';
  }
  
  return logs.map(log => {
    const location = log.location ? ` [${log.location}]` : '';
    return `[${log.type}]${location}: ${log.text}`;
  }).join('\n');
}

export { expect };
