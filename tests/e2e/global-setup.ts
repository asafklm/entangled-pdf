import { spawn, ChildProcess } from 'child_process';
import { createServer } from 'net';
import { join } from 'path';
import { writeFileSync, existsSync, unlinkSync } from 'fs';

// Disable TLS verification for self-signed test certificates
// Must be set before any fetch calls
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

const PROJECT_ROOT = join(__dirname, '..', '..');
const CERTS_DIR = join(PROJECT_ROOT, 'certs');
const DEFAULT_API_KEY = 'test-api-key-playwright-12345';
const SERVER_INFO_FILE = join(PROJECT_ROOT, '.test-servers.json');

interface ServerInfo {
  httpsPort: number;
  httpPort: number;
  httpsInversePort: number;
  apiKey: string;
}

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

async function waitForServer(port: number, https: boolean, timeout: number = 15000): Promise<void> {
  const startTime = Date.now();
  const protocol = https ? 'https' : 'http';
  
  while (Date.now() - startTime < timeout) {
    try {
      const url = `${protocol}://localhost:${port}/state`;
      console.log(`Trying to connect to ${url}...`);
      const response = await fetch(url, {
        signal: AbortSignal.timeout(1000),
      });
      console.log(`Response status: ${response.status}`);
      if (response.ok) {
        console.log(`Server is ready on port ${port}`);
        return;
      }
    } catch (err) {
      console.log(`Connection error: ${err}`);
    }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  
  throw new Error(`Server did not start within ${timeout}ms`);
}

async function startServerInstance(port: number, https: boolean, inverseSearch: boolean = false): Promise<ChildProcess> {
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
    PDF_SERVER_API_KEY: DEFAULT_API_KEY,
    PDF_SERVER_TESTING: '1',
    PDF_SERVER_TEST_MODE: '1',
    NODE_TLS_REJECT_UNAUTHORIZED: '0',
  };

  // Use project venv Python from .venv directory
  // The venv has all dependencies (uvicorn, fastapi, etc.) installed
  const venvPython = join(PROJECT_ROOT, '.venv', 'bin', 'python');
  const proc = spawn(venvPython, args, {
    cwd: PROJECT_ROOT,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  proc.stdout?.on('data', (data) => {
    console.log(`[Server ${https ? 'HTTPS' : 'HTTP'}${inverseSearch ? ' Inverse' : ''} stdout] ${data}`);
  });
  proc.stderr?.on('data', (data) => {
    console.error(`[Server ${https ? 'HTTPS' : 'HTTP'}${inverseSearch ? ' Inverse' : ''} stderr] ${data}`);
  });

  await waitForServer(port, https);
  return proc;
}

async function stopServer(proc: ChildProcess | null, name: string): Promise<void> {
  if (!proc) return;
  
  return new Promise((resolve) => {
    proc.on('exit', () => {
      console.log(`${name} server stopped`);
      resolve();
    });
    proc.kill('SIGTERM');
    setTimeout(() => {
      if (!proc.killed) {
        proc.kill('SIGKILL');
      }
      resolve();
    }, 5000);
  });
}

export default async function globalSetup() {
  console.log('Starting test servers...');
  
  const httpsPort = await findAvailablePort(18080);
  
  console.log(`Starting HTTPS server on port ${httpsPort}...`);
  const httpsProc = await startServerInstance(httpsPort, true);
  console.log(`HTTPS server started on port ${httpsPort}`);
  
  // Find HTTP port after HTTPS server has started
  const httpPort = await findAvailablePort(18090);
  console.log(`Starting HTTP server on port ${httpPort}...`);
  const httpProc = await startServerInstance(httpPort, false);
  console.log(`HTTP server started on port ${httpPort}`);
  
  // Find HTTPS inverse port after HTTP server has started
  const httpsInversePort = await findAvailablePort(18100);
  console.log(`Starting HTTPS server with inverse search on port ${httpsInversePort}...`);
  const httpsInverseProc = await startServerInstance(httpsInversePort, true, true);
  console.log(`HTTPS server with inverse search started on port ${httpsInversePort}`);
  
  // Save server info to file
  const serverInfo: ServerInfo = {
    httpsPort,
    httpPort,
    httpsInversePort,
    apiKey: DEFAULT_API_KEY,
  };
  writeFileSync(SERVER_INFO_FILE, JSON.stringify(serverInfo));
  
  // Return teardown function
  return async () => {
    console.log('Stopping test servers...');
    await Promise.all([
      stopServer(httpsProc, 'HTTPS'),
      stopServer(httpProc, 'HTTP'),
      stopServer(httpsInverseProc, 'HTTPS Inverse'),
    ]);
    if (existsSync(SERVER_INFO_FILE)) {
      unlinkSync(SERVER_INFO_FILE);
    }
  };
}

export { ServerInfo, SERVER_INFO_FILE, DEFAULT_API_KEY };
