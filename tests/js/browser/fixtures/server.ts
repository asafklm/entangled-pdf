import { spawn, ChildProcess } from 'child_process';
import { createServer } from 'net';
import { readFile } from 'fs/promises';
import { join } from 'path';

export interface ServerOptions {
  https?: boolean;
  port?: number;
  inverseSearch?: boolean;
  apiKey?: string;
}

export interface ServerInfo {
  port: number;
  baseUrl: string;
  wsUrl: string;
  apiKey: string;
  process: ChildProcess;
  stop: () => Promise<void>;
}

const PROJECT_ROOT = join(import.meta.dirname, '..', '..', '..', '..');
const CERTS_DIR = join(PROJECT_ROOT, 'certs');
const DEFAULT_API_KEY = 'test-api-key-playwright-12345';

/**
 * Find an available port on localhost
 */
async function findAvailablePort(startPort: number = 18000): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.listen(startPort, '127.0.0.1', () => {
      const address = server.address();
      const port = typeof address === 'object' && address ? address.port : startPort;
      server.close(() => resolve(port));
    });
    server.on('error', (err: NodeJS.ErrnoException) => {
      if (err.code === 'EADDRINUSE') {
        resolve(findAvailablePort(startPort + 1));
      } else {
        reject(err);
      }
    });
  });
}

/**
 * Wait for server to be ready by checking if port is accepting connections
 */
async function waitForServer(port: number, timeout: number = 10000): Promise<void> {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    try {
      const response = await fetch(`https://localhost:${port}/state`, {
        signal: AbortSignal.timeout(1000),
      });
      if (response.ok) {
        return;
      }
    } catch {
      // Server not ready yet
    }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  
  throw new Error(`Server did not start within ${timeout}ms`);
}

/**
 * Start the PDF server for testing
 */
export async function startServer(options: ServerOptions = {}): Promise<ServerInfo> {
  const {
    https = true,
    port = await findAvailablePort(),
    inverseSearch = false,
    apiKey = DEFAULT_API_KEY,
  } = options;

  const args = [
    join(PROJECT_ROOT, 'main.py'),
    '--port', String(port),
  ];

  if (https) {
    args.push(
      '--ssl-cert', join(CERTS_DIR, 'test.pem'),
      '--ssl-key', join(CERTS_DIR, 'test-key.pem')
    );
  } else {
    args.push('--http');
  }

  if (inverseSearch) {
    args.push('--inverse-search-nvim');
  }

  const env = {
    ...process.env,
    PDF_SERVER_API_KEY: apiKey,
    PDF_SERVER_TESTING: '1',
  };

  const serverProcess = spawn('python3', args, {
    cwd: PROJECT_ROOT,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  // Log server output for debugging
  serverProcess.stdout?.on('data', (data) => {
    console.log(`[Server stdout] ${data}`);
  });
  serverProcess.stderr?.on('data', (data) => {
    console.error(`[Server stderr] ${data}`);
  });

  // Wait for server to be ready
  await waitForServer(port);

  const protocol = https ? 'https' : 'http';
  const wsProtocol = https ? 'wss' : 'ws';

  return {
    port,
    baseUrl: `${protocol}://localhost:${port}`,
    wsUrl: `${wsProtocol}://localhost:${port}`,
    apiKey,
    process: serverProcess,
    stop: async () => {
      return new Promise((resolve) => {
        serverProcess.on('exit', () => resolve());
        serverProcess.kill('SIGTERM');
        // Force kill after 5 seconds if not dead
        setTimeout(() => {
          if (!serverProcess.killed) {
            serverProcess.kill('SIGKILL');
          }
          resolve();
        }, 5000);
      });
    },
  };
}
