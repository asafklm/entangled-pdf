# AGENTS.md - Coding Guidelines for PdfServer

## Project Overview

Python-based PDF server using FastAPI, WebSockets, and TypeScript for real-time PDF synchronization with SyncTeX support for LaTeX **forward search** (Editor → PDF) and **inverse search** (PDF → Editor via Shift+Click).

## Build / Test / Run Commands

```bash
# Python (using project venv)
# Start server with inverse search for Neovim
./bin/pdf-server start --inverse-search-nvim

# Start server on custom port
./bin/pdf-server start --port 9000

# Check server status (also shows authentication token)
./bin/pdf-server status

# Load PDF with forward search
./bin/pdf-server sync document.pdf 42:5:chapter.tex

# Run server directly (foreground mode for debugging)
./bin/python main.py --inverse-search-nvim --foreground
./bin/uvicorn main:app --reload --port 8001

# Python tests
./bin/python -m pytest tests/test_config.py -v
./bin/python -m pytest tests/test_config.py::test_function -v
./bin/python -m pytest tests/test_sync_unit.py -v                    # sync.py unit tests
./bin/python -m pytest tests/test_sync_e2e_subprocess.py -v          # E2E tests with real server
./bin/python -m pytest tests/test_sync_client_utils.py -v           # Client utility tests

# E2E test configuration (optional)
export PDF_SERVER_TEST_PORT=18080    # Default: 18080
./bin/python -m pytest tests/test_sync_e2e_subprocess.py -v

# TypeScript/JavaScript
npm run build        # Compile TypeScript
npm run typecheck    # Type check only
npm test             # Run Vitest unit tests
npm test -- --watch # Watch mode
npm run test:e2e     # Run Playwright E2E tests
npm run test:e2e:ui  # Run E2E tests with UI

# Webhook testing
http POST localhost:8001/webhook/update X-API-Key:super-secret-123 page:=2 y:=221.19
```

## IMPORTANT: Authentication Token Display

**When starting the server with `--inverse-search-nvim` or similar flags, ALWAYS show the authentication token at the end of your reply.** The token is required for accessing the PDF viewer when inverse search is enabled. Example:

```
Server running on port 8431
  Status: Ready
  PDF: /path/to/document.pdf
  Authentication Token: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
  URL: https://localhost:8431/view
```

The token is displayed by the server on startup and can also be retrieved via `pdf-server status`.

## Python Code Style

### Imports
```python
import argparse
import html

import uvicorn
from fastapi import FastAPI, HTTPException
from pathlib import Path
from typing import Set, Optional

from src.config import init_settings
```
- Group: stdlib → third-party → local
- Use absolute imports, alphabetical within groups
- Separate groups with blank lines

### Formatting & Types
- PEP 8, 4 spaces, 88 char max line, double quotes
- Type hints required: `def func(x: int) -> str:`
- Use `Optional`, `List`, `Dict` from `typing`

### Naming & Error Handling
- `snake_case` variables/functions, `PascalCase` classes, `UPPER_CASE` constants
- Specific exceptions only, never bare `except:`
- Use `HTTPException` for web errors

```python
# Good
except WebSocketDisconnect:
    manager.disconnect(websocket)

# Avoid
except:
    pass  # Only when data loss is acceptable
```

### Documentation
- Docstrings for public functions (Google style)
- Keep concise, comment non-obvious logic
- Include attribution for borrowed code

## TypeScript Code Style

### General
- Strict mode enabled in tsconfig.json
- Always annotate parameters and return types
- Prefer `interface` for objects, `type` for unions
- Avoid `any`, use `unknown` when needed
- Use `===`, prefer `const` over `let`
- Check `null` AND `undefined`: `if (value == null)`

### Canvas Rendering (PDF.js)
```typescript
const dpr: number = window.devicePixelRatio || 1;
const renderScale: number = (cssHeight * dpr) / internalHeight;
canvas.style.width = Math.round(viewport.width) + 'px';
canvas.width = Math.round(viewport.width * dpr);
```

### Mobile Safari Compatibility
- Use `scrollTo()` not `scrollTop`
- Wrap scroll in `requestAnimationFrame` + `setTimeout`
- Avoid flexbox with `overflow-y: auto`
- Round scroll positions: `Math.round(value)`

### Template Safety
```javascript
// In HTML template
window.PDF_CONFIG = { port: {{ port }}, filename: "{{ filename }}" };

// In JavaScript
const CONFIG = window.PDF_CONFIG || { port: 8431, filename: 'document.pdf' };
```

## FastAPI/WebSocket Patterns

### Endpoint Pattern
```python
@app.post("/webhook/update")
async def receive_webhook(data: dict, x_api_key: str = Header(None)):
    if x_api_key != SHARED_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    page = int(data.get("page", 1))
    x = data.get("x")
    y = data.get("y")
    
    await manager.broadcast({"action": "synctex", "page": page, "x": x, "y": y})
    return {"status": "success", "page": page, "x": x, "y": y}
```

### Connection Manager
```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    async def broadcast(self, message: dict):
        disconnected = set()
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception as e:
                disconnected.add(conn)
                logger.warning(f"Failed to send: {e}")
        for conn in disconnected:
            self.disconnect(conn)
```

## File Structure

```
./
├── main.py                    # Server entry point
├── bin/
│   └── pdf-server            # Server lifecycle management (start/stop/status/sync)
├── src/
│   ├── config.py              # Pydantic settings
│   ├── connection_manager.py   # WebSocket connections
│   ├── logging_config.py       # XDG-compliant logging setup
│   ├── state.py                # PDF state tracking (includes token generation)
│   └── routes/                 # API endpoints
│       ├── auth.py             # Token authentication endpoint
│       ├── load_pdf.py         # PDF loading API
│       ├── view.py             # HTML viewer with auth check
│       ├── websocket.py        # WebSocket with token validation
│       └── ...
├── static/                     # Frontend TypeScript
│   ├── viewer.ts               # Main viewer (includes shift+click handler)
│   ├── viewer.html             # Jinja2 template with token support
│   ├── token_form.html         # Authentication form
│   └── ...
├── examples/                   # Test PDF and LaTeX files
│   ├── example.pdf             # Sample PDF for testing
│   ├── example.tex             # Sample LaTeX source  
│   ├── example.synctex.gz      # SyncTeX data for testing
│   ├── test-pdf2.pdf           # Second PDF for switch testing
│   ├── test-pdf2.tex           # Second LaTeX source
│   └── test-pdf2.synctex.gz    # SyncTeX data for second PDF
├── tests/
│   ├── test_inverse_search.py  # Inverse search tests
│   └── ...
```

## Security

- Never hardcode secrets (use env vars: `PDF_SERVER_API_KEY`)
- Validate all input data
- Use X-API-Key pattern for authentication
- Escape HTML template variables
- **Inverse Search Security**: 
  - Only enabled with HTTPS/WSS (HTTP mode disables it)
  - Token-based auth (Jupyter-style) required for WebSocket connections
  - Secure cookies: httpOnly, secure, sameSite=strict
  - Template interpolation: only `%{line}` and `%{file}` allowed
  - Token regeneration on each PDF load

## Git Workflow

1. Check status: `git status`
2. Review diff: `git diff <file>`
3. Stage: `git add <file>`
4. Commit only when explicitly requested: `git commit -m "Description"`

## Dependencies

**Python**: fastapi, uvicorn, websockets, pydantic-settings, jinja2, requests, responses, pytest, pytest-asyncio, httpx
**TypeScript**: typescript, vitest, happy-dom, @types/node, pdfjs-dist, @playwright/test

When adding deps, prefer packages already in use.

## E2E Testing with Console Log Capture

### Capturing Browser Console Logs in Tests

For debugging complex WebSocket/frontend issues, use the `captureConsoleLogs()` helper:

```typescript
import { captureConsoleLogs, formatConsoleLogs } from './fixtures';

test('example with console debugging', async ({ page }) => {
  const consoleLogs: ConsoleLog[] = [];
  const stopCapture = captureConsoleLogs(page, consoleLogs);
  
  try {
    // ... test code ...
  } catch (e) {
    // On failure, log all captured console messages
    console.log('\n=== Browser Console Logs ===');
    console.log(formatConsoleLogs(consoleLogs));
    console.log('=== End Console Logs ===\n');
    throw e;
  } finally {
    stopCapture();
  }
});
```

The helper captures:
- All `console.log/info/warn/error` calls
- Page errors (JavaScript exceptions)
- Location information (file:line:column)

Logs are automatically printed to the test runner output with `[Browser Console]` prefix.

## Distribution Strategy

**Current (Development Phase):**
- Install via git clone + pip install
- Users must have git knowledge
- No PyPI publication yet (project not mature)

**Future (Post-Maturation):**
- Publish to PyPI
- Recommend pipx for end-user installation: `pipx install pdfserver`
- pipx provides isolated environments perfect for CLI tools
- Avoid pip for end-users (can cause dependency conflicts)

**Not Planned:**
- Homebrew distribution (requires tap maintenance)
- Standalone binaries (complex Node.js build integration)

**Rationale:** Target users (LaTeX + Neovim) already have Python installed. pipx is the modern standard for Python CLI tools and provides the best user experience without requiring git knowledge.
