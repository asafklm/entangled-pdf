# AGENTS.md - Coding Guidelines for EntangledPdf

## Project Overview

Python-based PDF server using FastAPI, WebSockets, and TypeScript for real-time PDF synchronization with SyncTeX support for LaTeX **forward search** (Editor → PDF) and **inverse search** (PDF → Editor via Shift+Click).

**Important Context**: This is a specialized tool for a specific workflow (editing LaTeX on remote servers). See [docs/intended-users-and-use-cases.md](docs/intended-users-and-use-cases.md) for detailed user context.

## Documentation Tone and Style

When writing or editing project documentation (README, guides, etc.):

- **Be honest**: Clearly state what the tool does and doesn't do
- **Be welcoming**: Don't push users away, but help them understand if the tool fits their needs
- **No sales pitch**: Don't try to persuade users that this is "better" than alternatives
- **Acknowledge limitations**: It's okay to say "you probably don't need this if..."
- **Context over features**: Explain the workflow and use case, not just feature lists

**Example of good tone:**
> "EntangledPdf is designed for a specific scenario: editing LaTeX on a remote, headless server. If you work locally with TeXShop or Zathura, you likely don't need this tool."

**Example of tone to avoid:**
> "EntangledPdf is the ultimate PDF viewer with unmatched multi-device synchronization!"

## First Principles

### When Debugging Complex Issues

**ALWAYS map the data flow before proposing fixes.**

For bugs involving:
- Timing issues
- WebSocket/HTTP synchronization
- Race conditions
- State management problems

**Required approach:**
1. Write failing test
2. **Map data flow** (server → client, what data, when)
3. **Scenario analysis** (what if X before Y? Y before X?)
4. Identify root cause
5. Propose fix + verify with scenarios
6. Implement with logging

See [Debugging Process for Complex Issues](#debugging-process-for-complex-issues) for detailed workflow.

## Build / Test / Run Commands

```bash
# Python (using project venv)
# Start server with inverse search for Neovim
./bin/entangle-pdf start --inverse-search-nvim

# Start server on custom port
./bin/entangle-pdf start --port 9000

# Check server status (also shows authentication token)
./bin/entangle-pdf status

# Load PDF with forward search
./bin/entangle-pdf sync document.pdf 42:5:chapter.tex

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
export ENTANGLEDPDF_TEST_PORT=18080    # Default: 18080
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

The token is displayed by the server on startup and can also be retrieved via `entangle-pdf status`.

## Python Code Style

### Imports
```python
import argparse
import html

import uvicorn
from fastapi import FastAPI, HTTPException
from pathlib import Path
from typing import Set, Optional

from entangledpdf.config import init_settings
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
│   └── entangle-pdf            # Server lifecycle management (start/stop/status/sync)
├── entangledpdf/
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

- Never hardcode secrets (use env vars: `ENTANGLEDPDF_API_KEY`)
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

### External Dependencies

For external tools that EntangledPdf depends on (e.g., synctex, neovim-remote), **do not create installation instructions in our documentation**. Instead:

1. **Link to official documentation** - Point users to the upstream project's docs
2. **Mention package names if known** - e.g., "texlive-extra-utils provides synctex"
3. **Avoid OS-specific instructions** - Different OS/package managers have different packages

**Rationale**: External projects may change their installation process. By linking to official docs, we avoid tight coupling and reduce maintenance burden when external projects update.

**Example**:
```markdown
# Instead of:
# apt install texlive-extra-utils  # Don't do this

# Do this:
# See https://www.tug.org/texlive/ for TeX Live installation
```

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

## Debugging Process for Complex Issues

When investigating bugs involving timing, WebSocket messages, or client-server synchronization:

### Required Steps (in order)

#### 1. Write Failing Test First
```typescript
test('descriptive test name showing scenario', async ({ page }) => {
  // Setup initial state
  // Trigger action
  // Verify expected behavior
});
```
- Verify the test fails for the RIGHT reason
- Ensure test is deterministic (not flaky)

#### 2. Map the Data Flow
**Before proposing ANY fix:**

```
Server                    Client
  │                         │
  ├─ broadcasts ───────────►├─ receives
  │   (what fields?)        │   (updates what state?)
  │                         │
  ├─ API response ────────►├─ uses
  │   (what data?)          │   (updates what state?)
```

- List ALL data dependencies
- Identify where each piece of state originates
- Note async boundaries (WebSocket, HTTP, timeouts)

#### 3. Scenario Analysis (REQUIRED for race conditions)

For each timing-sensitive code path, document:

**Scenario A: Event X before Event Y**
```
Timeline:
T0: Server sends message A
T1: Client receives A → updates State
T2: Event B occurs → what sees State?

Questions:
- What does handleMessageA() see in State?
- What does processEventB() see in State?
- Do they see consistent data?
```

**Scenario B: Event Y before Event X**
```
Timeline:
T0: Event B occurs
T1: Server sends message A
T2: Client receives A

Questions:
- What state does Event B check?
- Is it the same state after Message A?
```

**Create diagrams showing:**
- Message sequence (which direction, when)
- State changes at each point
- Decision points (if-statements that depend on state)

#### 4. Identify Root Cause

Ask these questions:
- Is data missing at decision point?
- Is state outdated when checked?
- Are we checking the wrong state variable?
- Is there an async gap where state changes?

**Common issues:**
- Server sends message without field X → client makes wrong decision
- Client checks State A → Server updates to B → Client uses stale A
- Two code paths update same state differently

#### 5. Propose Fix + Impact Analysis

For proposed fix, re-run scenarios:

```
Fix: Add pdf_file to broadcast message

Scenario A (WebSocket first):
T0: Broadcast with pdf_file → CONFIG.filename updated
T1: Poll /state → sees updated filename
Result: ✅ Consistent

Scenario B (Polling first):
T0: Poll /state → sees old filename
T1: Broadcast arrives → updates CONFIG.filename
T2: Next poll → sees updated filename
Result: ✅ Eventually consistent
```

Check edge cases:
- Initial load (no prior state)
- Rapid successive changes
- Network delays
- Error conditions

#### 6. Implementation Checklist

- [ ] Add logging FIRST (before fix code)
- [ ] Implement minimal fix
- [ ] Run failing test - should pass
- [ ] Run ALL related tests
- [ ] Check for regressions
- [ ] Remove debug logging (or convert to proper logs)

### Example: Race Condition in PDF [Switching](Switching)

**Initial investigation revealed:**
- Test: Load PDF1 via API, then sync to PDF2
- Expected: Show "Reload" button
- Actual: Auto-reloaded PDF2

**Data flow mapping:**
```
/api/load-pdf ──┬─► Server state updated
                ├─► Broadcast reload ──► Client reloads
                │                        (no filename!)
                └─► Returns filename

WebSocket synctex ──► Client handles
                      Checks CONFIG.filename
                      Sees "no-pdf-loaded" ❌
```

**Scenario analysis:**
```
T0: /api/load-pdf updates server state
T1: Broadcast reload → client reloads PDF1
    (but CONFIG.filename = "no-pdf-loaded"!)
T2: WebSocket synctex for PDF2 arrives
T3: handleSyncTeXMessage checks CONFIG.filename
    Still "no-pdf-loaded" → treats as initial load
    → auto-reloads PDF2 ❌
```

**Root cause:** Missing `pdf_file` in reload broadcast

**Fix:** Add `pdf_file` to broadcast, update client handler

**Impact verified:**
- Scenario A: ✅ Client knows filename before synctex
- Scenario B: ✅ Data flows correctly

### Key Principles

1. **Never fix before understanding** - Map first, fix second
2. **Scenario analysis is mandatory** - For timing-sensitive code
3. **Server-side first** - Often the root cause is server not sending data
4. **Log then fix** - Logging reveals actual behavior
5. **Test verifies understanding** - If test passes, your model is correct

## Distribution Strategy

**Current (Development Phase):**
- Install via git clone + pip install
- Users must have git knowledge
- No PyPI publication yet (project not mature)

**Future (Post-Maturation):**
- Publish to PyPI
- Recommend pipx for end-user installation: `pipx install entangledpdf`
- pipx provides isolated environments perfect for CLI tools
- Avoid pip for end-users (can cause dependency conflicts)

**Not Planned:**
- Homebrew distribution (requires tap maintenance)
- Standalone binaries (complex Node.js build integration)

**Rationale:** Target users (LaTeX + Neovim) already have Python installed. pipx is the modern standard for Python CLI tools and provides the best user experience without requiring git knowledge.

## Frontend Framework Decisions

### Current Status: Vanilla TypeScript

The project uses vanilla TypeScript with a modular architecture (see `static/*.ts`). This is intentional and appropriate for the current scale (~3,833 lines).

### Framework Analysis

Comprehensive analysis of Vue.js and Lit alternatives is documented in:

**📄 `[docs/frontend-framework-analysis.md](docs/frontend-framework-analysis.md)`**

Key findings:
- **Vue.js**: Too heavy (+40KB) for single-view PDF viewer, benefits don't justify costs
- **Lit**: Viable alternative (~5KB overhead), consider when codebase >6,000 lines or 5+ UI components
- **Current approach**: Continue with vanilla TypeScript, prepare for possible Lit migration in future

### When to Revisit

Consider Lit migration when:
- Codebase exceeds 6,000 lines
- Adding 3+ new UI components (search, annotations, settings)
- Team grows to 3+ developers
- Need to embed PDF viewer in other projects

### Progressive Adoption Path

1. **Now**: Continue vanilla TypeScript, extract UI logic into isolated modules
2. **When adding components**: Evaluate pain points in manual DOM manipulation
3. **At threshold**: Incremental migration to Lit (components → controllers → main app)

See the full analysis document for detailed comparison, code examples, and decision criteria.

## Debugging WebSocket Connection Issues

When diagnosing WebSocket connection problems in the browser:

### Key Console Logs to Look For

The frontend logs important diagnostic information to the browser console:

1. **Connection initiation:**
   ```
   Connecting to WebSocket...
   WebSocket token: abc12345...  (or null/undefined if not passed)
   WebSocket URL with token: wss://host:port/ws?token=***TOKEN***
   ```

2. **Connection state:**
   ```
   WebSocket connected
   WebSocket closed (code: 4001): Token required - user not authenticated
   WebSocket closed (code: 4002): Invalid token - server may have restarted
   ```

### Common WebSocket Close Codes

| Code | Meaning | Likely Cause |
|------|---------|--------------|
| 4001 | Token required | Inverse search enabled but no token passed to WebSocket |
| 4002 | Invalid token | Token doesn't match server (server restarted) |
| 1000 | Clean close | Normal disconnection |
| 1001 | Going away | Server shutting down |

### Debugging Steps

1. **Open browser console (F12)** before loading the page
2. **Look for the token** - should show first 8+ characters
3. **Check WebSocket URL** - should include `?token=...`
4. **Check close code** - 4001/4002 indicate auth issues

### Common Issues

**Token not passed to WebSocket:**
- Symptom: "WebSocket token: null/undefined"
- Check: Is the token in the HTML template? (`{{ token }}` in viewer.html)
- Check: Is the cookie being set after form submission? (auth.py)

**Token rejected:**
- Symptom: "WebSocket closed (code: 4002)"
- Cause: Server restarted, new token generated
- Fix: Re-authenticate in browser

**Connection immediately closed:**
- Symptom: "WebSocket closed (code: 4001)"
- Cause: Cookie not set or cookie token doesn't match server token
- Fix: Clear cookies and re-authenticate
