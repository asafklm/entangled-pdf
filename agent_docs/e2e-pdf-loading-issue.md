# E2E Test PDF Loading Issue

**Date:** 2026-04-23  
**Issue:** E2E tests show "No PDF Loaded" page despite API call to load PDF  
**Status:** Discovered during venv fix testing  
**Related:** Blocker for `feature/ctrl_click_inverse_search` E2E tests

## Problem Description

When running E2E tests for inverse search functionality, the tests fail because the PDF is not being loaded properly. The browser shows the "No PDF Loaded" page instead of the rendered PDF with canvas elements.

### Error Evidence

Test failure shows page snapshot:
```yaml
- generic [active] [ref=e1]:
  - generic [ref=e2]:
    - heading "No PDF Loaded" [level=2] [ref=e3]
    - paragraph [ref=e4]:
      - text: Use
      - code [ref=e5]: entangle-pdf sync <filename>
      - text: to load a PDF file.
  - generic [ref=e8] [cursor=pointer]: Connected
```

The test expects to find `locator('#viewer-container canvas').first()` but the canvas doesn't exist because the PDF wasn't loaded.

## Affected Tests

The following tests in `tests/e2e/inverse-search.spec.ts` fail:

1. `viewer includes inverse search UI elements`
2. `long-press shows inverse search tooltip with confirmation`
3. `long-press tooltip can be dismissed with Escape key`
4. `tooltip can be dismissed and re-shown`

And the new tests for Ctrl+Click:
5. `ctrl+click shows inverse search tooltip with confirmation`
6. `cmd+click (macOS) shows inverse search tooltip`
7. `regular click does not show inverse search tooltip`

## Current Test Setup

Each test follows this pattern:

```typescript
// 1. Load the PDF via API
await fetch(`${httpsInverseServer.baseUrl}/api/load-pdf`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': httpsInverseServer.apiKey,
  },
  body: JSON.stringify({
    pdf_path: EXAMPLE_PDF,  // Absolute path to examples/example.pdf
  }),
});

// 2. Get auth token and set cookie
const stateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
const stateData = await stateResponse.json();
const token = stateData.websocket_token;

await page.context().addCookies([{
  name: 'pdf_token',
  value: token,
  domain: 'localhost',
  path: '/',
  secure: true,
  httpOnly: true,
  sameSite: 'Strict',
}]);

// 3. Navigate to viewer
await page.goto(`${httpsInverseServer.baseUrl}/view`);

// 4. Wait for PDF to render - FAILS HERE
await expect(page.locator('#viewer-container canvas').first())
  .toBeVisible({ timeout: 10000 });
```

## Suspected Causes

### 1. API Call Failing Silently

The `/api/load-pdf` fetch might be failing without throwing an error. The response status and body are not being checked.

**Verification Needed:**
```typescript
const response = await fetch(...);
console.log('Load PDF response:', response.status, await response.text());
```

### 2. PDF Path Resolution

The `EXAMPLE_PDF` path is constructed as:
```typescript
const EXAMPLES_DIR = join(__dirname, '../../examples');
const EXAMPLE_PDF = join(EXAMPLES_DIR, 'example.pdf');
```

In the test runner context (Node.js), this resolves correctly. However, the server might have trouble accessing this path from its subprocess context.

**Verification Needed:**
- Check if path exists before API call
- Try using relative path from project root
- Check server logs for file access errors

### 3. Timing Issue

The PDF might take longer than expected to load. Currently the test waits 10 seconds, but perhaps:
- PDF.js initialization is slower
- Network fetch from server to load PDF is delayed
- Server hasn't finished processing the load-pdf request before browser navigates

**Potential Fix:**
```typescript
// Wait for PDF to be loaded via polling
await page.waitForFunction(() => {
  return document.querySelectorAll('#viewer-container canvas').length > 0;
}, { timeout: 15000 });
```

### 4. Missing State Update

After the `/api/load-pdf` API call, the server should broadcast a reload message to all connected clients. The browser page might not be receiving this update.

**Investigation:**
- Check if WebSocket connection is established before navigating
- Verify broadcast mechanism is working
- Check browser console for WebSocket messages

## Debugging Steps

### Step 1: Verify API Response

Add explicit response checking:

```typescript
test('debug PDF loading', async ({ page, httpsInverseServer }) => {
  const response = await fetch(`${httpsInverseServer.baseUrl}/api/load-pdf`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': httpsInverseServer.apiKey,
    },
    body: JSON.stringify({
      pdf_path: EXAMPLE_PDF,
    }),
  });
  
  console.log('Response status:', response.status);
  console.log('Response body:', await response.text());
  
  // Check if file exists
  const fs = require('fs');
  console.log('PDF exists:', fs.existsSync(EXAMPLE_PDF));
  console.log('PDF path:', EXAMPLE_PDF);
});
```

### Step 2: Check Server Logs

The server logs during E2E tests show:
```
[Server HTTPS stderr] 2026-04-23 16:57:45,280 - __main__ - INFO - No PDF loaded - waiting for entangle-pdf sync to load a PDF
```

But we don't see log output after the API call. Need to verify:
- Is the API endpoint being reached?
- Are there any errors during PDF loading?
- Does the server successfully read the PDF file?

### Step 3: Browser Console Logs

Capture browser console logs to see:
- JavaScript errors during PDF loading
- WebSocket connection status
- PDF.js initialization messages

### Step 4: Verify State Endpoint

Check what the state endpoint returns after load-pdf:

```typescript
const stateResponse = await fetch(`${httpsInverseServer.baseUrl}/state`);
const stateData = await stateResponse.json();
console.log('State:', stateData);
// Should show pdf_file: example.pdf, not null
```

## Historical Context

This issue may be related to:
- CI environment differences (headless Chrome vs. headed)
- File path accessibility from subprocess
- Race conditions between API call and page navigation

The tests were passing at some point (they exist in the codebase), so this is likely a regression or environment-specific issue.

## Next Actions

1. **Immediate:** Add debug logging to identify where the chain breaks
2. **Short-term:** Fix the PDF loading issue in test setup
3. **Long-term:** Add retry logic and better error messages to E2E tests

## Related Files

- `tests/e2e/inverse-search.spec.ts` - E2E test file
- `tests/e2e/global-setup.ts` - Server setup (spawn subprocess)
- `entangledpdf/routes/load_pdf.py` - API endpoint
- `static/viewer.ts` - Frontend viewer initialization
- `examples/example.pdf` - Test PDF file
