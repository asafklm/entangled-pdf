# AGENTS.md - Coding Guidelines for PdfServer

## Project Overview

Python-based PDF server using FastAPI, WebSockets, and TypeScript for real-time PDF synchronization with SyncTeX support for LaTeX **forward search** (Editor → PDF) and **inverse search** (PDF → Editor via Shift+Click).

## Build / Test / Run Commands

```bash
# Python (using project venv)
# Start server with inverse search for Neovim
/home/asaf/programming/PdfServer/bin/pdf-server start --inverse-search-nvim

# Start server on custom port
/home/asaf/programming/PdfServer/bin/pdf-server start --port 9000

# Check server status
/home/asaf/programming/PdfServer/bin/pdf-server status

# View logs
/home/asaf/programming/PdfServer/bin/pdf-server logs --follow

# Stop server
/home/asaf/programming/PdfServer/bin/pdf-server stop

# Load PDF with forward search
/home/asaf/programming/PdfServer/bin/sync-remote-pdf --synctex-forward "42:5:chapter.tex" document.pdf

# Run server directly (foreground mode for debugging)
/home/asaf/programming/PdfServer/bin/python main.py --inverse-search-nvim --foreground
/home/asaf/programming/PdfServer/bin/uvicorn main:app --reload --port 8001

# Python tests
/home/asaf/programming/PdfServer/bin/python -m pytest tests/test_config.py -v
/home/asaf/programming/PdfServer/bin/python -m pytest tests/test_config.py::test_function -v

# TypeScript/JavaScript
npm run build        # Compile TypeScript
npm run typecheck    # Type check only
npm test             # Run Vitest tests
npm test -- --watch # Watch mode

# Webhook testing
http POST localhost:8001/webhook/update X-API-Key:super-secret-123 page:=2 y:=221.19
```

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
/home/asaf/programming/PdfServer/
├── main.py                    # Server entry point
├── bin/
│   ├── pdf-server            # Server lifecycle management (start/stop/status/logs)
│   └── sync-remote-pdf       # LaTeX sync client (forward search only)
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
├── tests/
│   ├── test_inverse_search.py  # Inverse search tests
│   └── ...
```

## Security

- Never hardcode secrets (use env vars: `PDF_SERVER_SECRET`)
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
**TypeScript**: typescript, vitest, happy-dom, @types/node, pdfjs-dist

When adding deps, prefer packages already in use.
