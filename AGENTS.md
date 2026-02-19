# AGENTS.md - Coding Guidelines for Agentic Agents

## Project Overview

This is a Python-based PDF server application using FastAPI, WebSockets, and JavaScript/HTML for serving and synchronizing PDF viewing across devices. It integrates with Neovim/VimTex via SyncTeX for LaTeX forward search.

## Build / Test / Run Commands

```bash
# Run a Python file (using project venv)
/home/asaf/programming/PdfServer/bin/python <file.py>

# Run FastAPI server with PDF file argument
/home/asaf/programming/PdfServer/bin/python main.py examples/example.pdf port=8001

# Run FastAPI server (alternative)
/home/asaf/programming/PdfServer/bin/uvicorn main:app --reload --port 8001

# Run a single test file (when tests are added)
/home/asaf/programming/PdfServer/bin/python -m pytest <test_file.py> -v

# Run a single test function
/home/asaf/programming/PdfServer/bin/python -m pytest <test_file.py>::<test_function> -v

# Test webhook endpoint (using httpie)
/http POST localhost:8001/webhook/update X-API-Key:super-secret-123 page:=2 y:=221.19

# Type checking (when mypy is added)
/home/asaf/programming/PdfServer/bin/python -m mypy <file.py>

# Linting (when ruff is added)
/home/asaf/programming/PdfServer/bin/python -m ruff check <file.py>
/home/asaf/programming/PdfServer/bin/python -m ruff format <file.py>
```

## Code Style Guidelines

### Python - Imports
- Group imports: stdlib first, third-party second, local last
- Use absolute imports; avoid relative imports
- Sort imports alphabetically within groups
- Separate import groups with blank lines

```python
import argparse
import html

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
from typing import Set
```

### Python - Formatting
- Follow PEP 8
- 4 spaces for indentation
- Max line length: 88 characters (Black-compatible)
- Use double quotes for strings

### Python - Types
- Use type hints for function parameters and return values
- Use `typing` module for complex types (Optional, List, Dict, etc.)
- Example: `def func(x: int) -> str:`

### Python - Naming Conventions
- `snake_case` for variables, functions, methods
- `PascalCase` for classes
- `UPPER_CASE` for constants
- Private methods/vars: prefix with `_`

### Python - Error Handling
- Use specific exception types, not bare `except:`
- Always use `try/except` for network operations
- Use `HTTPException` from FastAPI for web errors
- Log errors appropriately; silent pass only when acceptable

```python
# Good: Specific exception
except WebSocketDisconnect:
    manager.disconnect(websocket)

# Avoid: Bare except
except:
    pass  # Only when data loss is acceptable
```

### Python - Documentation
- Use docstrings for public functions and classes (Google style)
- Keep docstrings concise but informative
- Comment non-obvious logic
- Include attribution for borrowed code per license

### JavaScript/HTML - General
- Use template literals for string interpolation
- Prefer `const` over `let`, avoid `var`
- Use `===` for equality checks (not `==`)
- Always check for `null` AND `undefined` when validating: `if (value == null)`

### JavaScript/HTML - Canvas Rendering (PDF.js)
When rendering PDFs with PDF.js, follow these patterns:

```javascript
// Calculate render scale correctly for high-DPI displays
const cssHeight = parseFloat(canvas.style.height);
const internalHeight = canvas.height;
const dpr = window.devicePixelRatio || 1;
const renderScale = (cssHeight * dpr) / internalHeight;

// Set both CSS display size AND internal canvas resolution
canvas.style.width = Math.round(viewport.width) + 'px';
canvas.style.height = Math.round(viewport.height) + 'px';
canvas.width = Math.round(viewport.width * dpr);
canvas.height = Math.round(viewport.height * dpr);
```

### JavaScript/HTML - Mobile Safari Compatibility
- Use `scrollTo()` method instead of `scrollTop` property for scrolling
- Wrap scroll operations in `requestAnimationFrame` + `setTimeout` for Safari
- Avoid flexbox with `overflow-y: auto` on same container (known Safari bugs)
- Use `text-align: center` + `display: inline-block` for page centering
- Round scroll positions to integers: `Math.round(value)`
- Check for both `null` and `undefined`: `if (y == null)`

### JavaScript/HTML - Template Safety
- Use Jinja2 templating with FastAPI's TemplateResponse for automatic escaping
- Pass configuration via `window` object, not template strings:

```javascript
// In HTML template:
<script>
    window.PDF_CONFIG = {
        port: {{ port }},
        filename: "{{ filename }}"
    };
</script>

// In JavaScript:
const CONFIG = window.PDF_CONFIG || { port: 8431, filename: 'document.pdf' };
```

## FastAPI/WebSocket Patterns

### Endpoint Pattern
```python
@app.post("/webhook/update")
async def receive_webhook(data: dict, x_api_key: str = Header(None)):
    """Receive page updates and SyncTeX forward search coordinates"""
    if x_api_key != SHARED_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    page = int(data.get("page", 1))
    x = data.get("x")  # Optional: PDF x coordinate from synctex
    y = data.get("y")  # Optional: PDF y coordinate from synctex
    
    await manager.broadcast({
        "action": "synctex",
        "page": page,
        "x": x,
        "y": y
    })
    
    return {"status": "success", "page": page, "x": x, "y": y}
```

### WebSocket Handler (Client-Side)
```javascript
const socket = new WebSocket(`ws://${window.location.hostname}:{{PORT}}/ws`);
socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.action === "synctex") {
        scrollToPage(data.page, data.x, data.y);
        if (data.y != null) {
            showRedDot(data.page, data.y);
        }
    }
};
```

### Connection Manager Pattern
```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except KeyError:
            pass

    async def broadcast(self, message: dict):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                disconnected.add(connection)
                logger.warning(f"Failed to send: {e}")
        
        # Clean up failed connections
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()
```

## Security

- Never hardcode secrets in production code
- Use environment variables for API keys/secrets
- Validate all incoming data before processing
- Use proper authentication headers (X-API-Key pattern shown)
- Always escape HTML template variables to prevent XSS

## File Structure

```
/home/asaf/programming/PdfServer/
├── main.py                 # Entry point
├── src/
│   ├── config.py          # Configuration management (Pydantic Settings)
│   ├── connection_manager.py  # WebSocket connection handling
│   ├── state.py           # PDF state tracking
│   └── routes/            # API endpoints
│       ├── __init__.py    # Route exports
│       ├── view.py        # HTML viewer endpoint (Jinja2 templates)
│       ├── pdf.py         # PDF file serving
│       ├── state.py       # Current state endpoint
│       ├── webhook.py     # SyncTeX webhook endpoint
│       ├── websocket.py   # WebSocket endpoint
│       └── static_files.py # Static file serving
├── static/                # Frontend assets
│   ├── viewer.html        # Jinja2 HTML template
│   └── viewer.js          # JavaScript viewer (PDF.js)
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── test_config.py     # Configuration tests
│   ├── test_connection_manager.py  # WebSocket tests
│   └── test_state.py      # State management tests
├── examples/              # Example PDFs and LaTeX files
│   ├── example.tex
│   └── example.pdf
├── pdfjs-dist/            # PDF.js library files
└── bin/, lib/, include/   # Virtual environment
```

## Dependencies

Key packages installed in venv:
- `fastapi`, `uvicorn` - Web server
- `websockets` - Real-time communication
- `requests` - HTTP client
- `pydantic`, `pydantic-settings` - Configuration management
- `jinja2` - HTML templating
- `python-multipart` - Form data parsing

Development dependencies:
- `pytest`, `pytest-asyncio` - Testing framework
- `httpx` - HTTP client for tests

When adding new dependencies, prefer packages already in use.

## Git Workflow

1. **Check status** before making changes: `git status`
2. **Review diff** before committing: `git diff <file>`
3. **Stage files**: `git add <file>`
4. **Commit** only when explicitly requested by user
5. **Commit message format**: Clear, concise description of what/why

```bash
git status
git diff <file>
git add <file>
git commit -m "Description of changes"
```

## Testing Best Practices

- Test webhook endpoints with httpie (cleaner than curl)
- Always verify server is running before testing
- Check browser console for JavaScript errors
- Test on both mobile (iPad Safari) and desktop for compatibility

## License Compliance

- Project is Apache 2.0 licensed
- When using external code, include attribution comments
- Follow third-party license requirements