import type { ServerInfo } from './server';

/**
 * Get the authentication token from the server status endpoint
 */
export async function getAuthToken(server: ServerInfo): Promise<string | null> {
  try {
    const response = await fetch(`${server.baseUrl}/status`, {
      headers: {
        'X-API-Key': server.apiKey,
      },
    });
    
    if (!response.ok) {
      return null;
    }
    
    const data = await response.json();
    return data.token || null;
  } catch {
    return null;
  }
}

/**
 * Navigate to a page with authentication token already set in cookie
 * 
 * This bypasses the token entry form by setting the cookie directly.
 */
export async function gotoWithAuth(
  page: { goto: (url: string) => Promise<unknown>; context: { addCookies: (cookies: unknown[]) => Promise<unknown> } },
  path: string,
  server: ServerInfo
): Promise<void> {
  const token = await getAuthToken(server);
  
  if (token) {
    // Set the authentication cookie before navigating
    await page.context.addCookies([{
      name: 'pdf_token',
      value: token,
      domain: 'localhost',
      path: '/',
      secure: true,
      httpOnly: true,
      sameSite: 'Strict',
    }]);
  }
  
  await page.goto(`${server.baseUrl}${path}`);
}

/**
 * Check if inverse search is enabled on the server
 */
export async function isInverseSearchEnabled(server: ServerInfo): Promise<boolean> {
  try {
    const response = await fetch(`${server.baseUrl}/status`, {
      headers: {
        'X-API-Key': server.apiKey,
      },
    });
    
    if (!response.ok) {
      return false;
    }
    
    const data = await response.json();
    return data.inverse_search_enabled === true;
  } catch {
    return false;
  }
}
