# Unix Socket Implementation Plan for Editor→Server Communication

**Status**: Draft  
**Branch**: `feature/unix-socket-cli`  
**Date**: 2026-05-04

## Overview

Replace TCP/HTTPS communication between `entangle-pdf sync` (CLI) and the server with **Unix domain sockets**. The browser-facing TCP+HTTPS+WebSocket interface remains unchanged.

## Goals

1. **Security**: Only the user who started the server can connect (filesystem permissions on socket)
2. **Simplicity**: Remove API key requirement for local CLI commands
3. **Consistency**: Align with existing nvr (Neovim remote) Unix socket communication pattern
4. **Reliability**: Proper cleanup of socket files on shutdown/crash

## Architecture: Dual Transport

Run two Uvicorn ASGI servers in the same Python `asyncio` event loop. They share global singletons (`pdf_state`, `ConnectionManager`).

| Server | Transport | Routes | Audience |
|--------|-----------|--------|----------|
| **Admin Server** | Unix Domain Socket | `/api/load-pdf`, `/webhook/update`, `/state` | `entangle-pdf sync`, `status` |
| **Browser Server** | TCP + HTTPS (`0.0.0.0:PORT`) | `/view`, `/auth`, `/ws`, `/pdf`, `/state`, static files | Browser / WebSocket clients |

### Why This Works

Uvicorn accepts `uds="..."` and can run multiple `Server` instances via `asyncio.gather()`. Both apps import the same module-level state objects, so an admin command on the socket broadcasts to browser WebSockets over TCP.

## File Structure Changes

### New Files

```
entangledpdf/
├── socket_path.py          # Socket filesystem path management
├── admin_app.py            # FastAPI instance for admin routes
└── browser_app.py          # FastAPI instance for browser routes
```

### Modified Files

```
entangledpdf/
├── main.py                 # Dual-server runner with socket lifecycle
├── sync.py                 # Unix socket HTTP client (no more TCP/HTTPS)
└── cli.py                  # Update sync, status; socket-based server check
```

## Implementation Details

### 1. Socket Path Management (`socket_path.py`)

**Path Resolution** (in order of preference):
1. `$ENTANGLEDPDF_SOCKET` environment variable
2. `$XDG_RUNTIME_DIR/entangledpdf/server.sock`
3. `$HOME/.local/run/entangledpdf/server.sock`

**Startup Behavior**:
```python
def ensure_socket_ready(socket_path: Path) -> None:
    """Check for stale socket, remove if dead, error if live server."""
    if not socket_path.exists():
        socket_path.parent.mkdir(parents=True, mode=0o700)
        return
    
    # Socket exists - check if server is actually listening
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(str(socket_path))
        sock.close()
        raise RuntimeError(f"Server already running (socket: {socket_path})")
    except ConnectionRefusedError:
        # Stale socket - remove it
        socket_path.unlink()
```

**Permissions**:
- Parent directory: `0700` (only owner can read/write)
- Socket file: `0600` (automatic via bind + umask)

### 2. Split FastAPI Apps

#### `admin_app.py`

```python
from fastapi import FastAPI

app = FastAPI(title="EntangledPdf Admin")

# Admin-only routes (no auth required - socket auth is sufficient)
app.include_router(load_pdf.router)
app.include_router(webhook.router)
app.include_router(state.router)
# Note: No stop command - Ctrl+C or kill signal is sufficient
```

#### `browser_app.py`

```python
from fastapi import FastAPI

app = FastAPI(title="EntangledPdf Browser")

# Browser-facing routes
app.include_router(view.router)
app.include_router(auth.router)
app.include_router(websocket.router)
app.include_router(pdf.router)
app.include_router(state.router)  # Mounted on both
static_files.setup_static_files(app)
```

### 3. Dual Server Runner (`main.py`)

```python
async def run_servers():
    socket_path = get_socket_path()
    ensure_socket_ready(socket_path)
    
    # Admin server on Unix socket
    admin_config = uvicorn.Config(
        "entangledpdf.admin_app:app",
        uds=str(socket_path),
        loop="asyncio",
        log_level="warning"
    )
    
    # Browser server on TCP + HTTPS (as today)
    browser_config = uvicorn.Config(
        "entangledpdf.browser_app:app",
        host=settings.host,
        port=settings.port,
        ssl_keyfile=str(ssl_key) if ssl_config else None,
        ssl_certfile=str(ssl_cert) if ssl_config else None,
        loop="asyncio",
        log_level="info" if args.verbose else "warning"
    )
    
    admin_server = uvicorn.Server(admin_config)
    browser_server = uvicorn.Server(browser_config)
    
    # Setup signal handlers for clean shutdown
    def signal_handler(sig, frame):
        socket_path.unlink(missing_ok=True)
        admin_server.should_exit = True
        browser_server.should_exit = True
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await asyncio.gather(admin_server.serve(), browser_server.serve())
```

**Shutdown Behavior**:
- `SIGINT`/`SIGTERM`: Unlink socket file, then exit
- Crash/unclean exit: Socket file may remain. Handled automatically at next startup via stale socket detection.

### 4. Unix Socket HTTP Client (`sync.py`)

Replace all TCP/HTTPS logic with a pure-Python Unix socket HTTP client:

```python
import http.client
import socket as socket_module
from pathlib import Path

class UnixHTTPConnection(http.client.HTTPConnection):
    """HTTP connection over Unix domain socket."""
    
    def __init__(self, socket_path: str):
        super().__init__("localhost")
        self.socket_path = socket_path
    
    def connect(self):
        self.sock = socket_module.socket(socket_module.AF_UNIX, socket_module.SOCK_STREAM)
        self.sock.connect(self.socket_path)


def send_request(
    method: str,
    path: str,
    socket_path: Path,
    data: Optional[dict] = None
) -> dict:
    """Send HTTP request over Unix socket.
    
    No API key, no SSL, no port needed.
    """
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    
    conn = UnixHTTPConnection(str(socket_path))
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        return json.loads(response.read().decode("utf-8"))
    except http.client.HTTPException as e:
        raise Exception(f"HTTP error: {e}")
    finally:
        conn.close()


def get_default_socket_path() -> Path:
    """Get default socket path based on XDG conventions."""
    return socket_path.get_socket_path()


def load_pdf(pdf_path: Path, socket_path: Optional[Path] = None) -> dict:
    """Load PDF via Unix socket."""
    socket_path = socket_path or get_default_socket_path()
    return send_request("POST", "/api/load-pdf", socket_path, 
                       {"pdf_path": str(pdf_path.resolve())})


def forward_search(line: int, column: int, tex_file: str, pdf_file: str,
                   socket_path: Optional[Path] = None) -> dict:
    """Perform forward search via Unix socket."""
    socket_path = socket_path or get_default_socket_path()
    data = {
        "line": line,
        "col": column,
        "tex_file": tex_file,
        "pdf_file": str(Path(pdf_file).resolve())
    }
    return send_request("POST", "/webhook/update", socket_path, data)
```

**Removed**: `port`, `use_http`, `ssl_context`, `api_key` parameters.

### 5. CLI Updates (`cli.py`)

#### `cmd_start` (Updated)

```python
def cmd_start(args):
    # Check if server already running via socket
    socket_path = get_socket_path()
    if socket_path.exists():
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(str(socket_path))
            sock.close()
            print(f"Error: Server already running", file=sys.stderr)
            print(f"Socket: {socket_path}", file=sys.stderr)
            return 1
        except ConnectionRefusedError:
            # Stale socket - will be cleaned up on startup
            pass
    
    # Start server as subprocess (same as today)
    # ... rest unchanged
```

#### `cmd_sync` (Updated)

```python
def cmd_sync(args):
    """Load PDF and optionally perform forward search via Unix socket."""
    socket_path = args.socket_path or get_default_socket_path()
    
    try:
        response = load_pdf(args.pdf_file, socket_path)
        
        if args.synctex:
            line, column, tex_file = parse_synctex_forward(args.synctex)
            search_response = forward_search(
                line, column, str(tex_file), str(args.pdf_file), socket_path
            )
            # ... handle response
        
        print(f"PDF loaded: {response.get('pdf_file')}")
        return 0
        
    except FileNotFoundError:
        print(f"Error: Server not running (socket not found: {socket_path})", 
              file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
```

**Removed flags**: `--api-key`, `--http`, `--port` (sync now uses socket)

**New flag**: `--socket-path` (optional override)

#### `cmd_status` (Updated)

```python
def cmd_status(args):
    """Show server status via Unix socket."""
    socket_path = args.socket_path or get_default_socket_path()
    
    try:
        state = send_request("GET", "/state", socket_path)
    except (FileNotFoundError, ConnectionRefusedError):
        print(f"Server not running (socket: {socket_path})")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    # Display status (same as today, but no auth token needed)
    print(f"Server running")
    print(f"  Status: {'Ready' if state.get('pdf_loaded') else 'Waiting for PDF'}")
    print(f"  PDF: {state.get('pdf_file', 'None')}")
    print(f"  Socket: {socket_path}")
    
    # Note: Browser URLs still use TCP port - display from state
    if state.get('port'):
        # ... display browser URLs as today
        pass
```

**Removed flags**: `--port` (uses socket)

**New flag**: `--socket-path` (optional override)

### 6. Socket File Lifecycle

| Scenario | Action |
|----------|--------|
| **Server startup** | Resolve path. If socket exists and `connect()` succeeds → error. If `connect()` fails → unlink stale socket, then bind. |
| **Normal stop (Ctrl+C)** | Signal handler removes socket. |
| **Kill signal (SIGTERM)** | Signal handler removes socket. |
| **Crash / unclean exit** | Socket file remains. Handled automatically at next startup (stale socket detection). |
| **Permissions** | Directory: `0700`. Socket file: `0600` (enforced by OS on bind). |

## Decision: Stop Command

**Decision**: Do NOT implement a `stop` command.

**Rationale**:
1. With proper stale socket cleanup on startup, a crashed server is automatically detected and cleaned up on next start
2. The server runs in foreground mode (Ctrl+C is the expected way to stop)
3. Kill signals (`SIGTERM`, `SIGINT`) are handled cleanly with socket removal
4. A `stop` command would require the server to accept external shutdown signals, which adds complexity without clear benefit for a foreground-only process
5. Users can always use `kill` or `pkill` if needed, and the socket will be cleaned on next startup

**Exception**: If users report confusion about "how to stop the server", we can revisit this decision later.

## Tooling Decision: curl vs nc

**Question**: For manual debugging/documentation, which tool should we recommend for HTTP over Unix sockets?

### Option A: curl

```bash
# GET request
curl --unix-socket /run/user/1000/entangledpdf/server.sock \
     http://localhost/state

# POST request
curl --unix-socket /run/user/1000/entangledpdf/server.sock \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"pdf_path": "/path/to/file.pdf"}' \
     http://localhost/api/load-pdf
```

**Pros**:
- Most developers already know curl
- Native HTTP support (headers, methods, JSON)
- Widely installed on all systems
- Clear syntax for HTTP operations

**Cons**:
- The `http://localhost` URL is a placeholder (ignored when using `--unix-socket`)
- Slightly less intuitive for socket newcomers

### Option B: nc (netcat)

```bash
# GET request
printf 'GET /state HTTP/1.0\r\n\r\n' | nc -U /run/user/1000/entangledpdf/server.sock

# POST request (more verbose)
{
  printf 'POST /api/load-pdf HTTP/1.0\r\n'
  printf 'Content-Type: application/json\r\n'
  printf 'Content-Length: %d\r\n\r\n' 35
  printf '{"pdf_path": "/path/to/file.pdf"}'
} | nc -U /run/user/1000/entangledpdf/server.sock
```

**Pros**:
- Shows raw HTTP protocol (educational)
- Lower-level tool

**Cons**:
- Requires manual HTTP formatting (headers, content-length)
- More error-prone
- Different netcat variants (OpenBSD, traditional, GNU) have different flags
- Not all systems have `-U` flag support (Debian needs `netcat-openbsd` package)

### Decision: Use curl

**Rationale**:
1. **Standard**: curl is the de facto standard for HTTP requests
2. **Simplicity**: No manual HTTP formatting needed
3. **Consistency**: Same tool for TCP and Unix socket HTTP (just add `--unix-socket`)
4. **Availability**: curl is installed on virtually every modern system
5. **Documentation**: Familiar syntax for users

**Note for documentation**: We'll mention that `--unix-socket` requires curl 7.40+ (released 2015), which is available on all modern distributions.

## Testing Changes

### Unit Tests

1. **`test_socket_path.py`** (new):
   - Path resolution order
   - Stale socket detection
   - Directory creation with correct permissions

2. **`test_sync_client_utils.py`** (update):
   - Replace TCP/HTTPS tests with Unix socket tests
   - Test `UnixHTTPConnection` class
   - Remove API key related tests

### E2E Tests

1. **`test_sync_e2e_subprocess.py`** (update):
   - Server subprocess now creates Unix socket in test tmp dir
   - `entangle-pdf sync` calls resolve to socket path
   - Browser/WebSocket tests continue using TCP/HTTPS

2. **New test**: Verify socket permissions (mode 0600)
3. **New test**: Verify stale socket cleanup on startup
4. **New test**: Verify "already running" detection

## Security Improvements Summary

| Aspect | Before | After |
|--------|--------|-------|
| **CLI Auth** | API key in env var or CLI flag | Filesystem permissions (socket mode 0600) |
| **Transport** | TCP + HTTPS with `CERT_NONE` bypass | Unix domain socket (no SSL needed) |
| **Other User Access** | Possible if API key known | Impossible (socket permissions) |
| **Browser Transport** | TCP + HTTPS (unchanged) | TCP + HTTPS (unchanged) |
| **Browser Auth** | Token + cookie (unchanged) | Token + cookie (unchanged) |

## Migration Guide (for AGENTS.md)

### Before

```bash
# Start server (foreground)
entangle-pdf start --inverse-search-nvim

# Sync (requires API key)
export ENTANGLEDPDF_API_KEY="secret123"
entangle-pdf sync document.pdf 42:5:chapter.tex

# Status (uses TCP)
entangle-pdf status --port 8431
```

### After

```bash
# Start server (foreground) - unchanged
entangle-pdf start --inverse-search-nvim

# Sync (no API key needed)
entangle-pdf sync document.pdf 42:5:chapter.tex

# Status (uses socket)
entangle-pdf status

# Manual socket path override (rarely needed)
entangle-pdf sync --socket-path /tmp/custom.sock document.pdf
```

## Implementation Checklist

- [ ] Create `socket_path.py` with path resolution and stale socket detection
- [ ] Create `admin_app.py` with admin-only routes
- [ ] Create `browser_app.py` with browser-only routes (refactored from `main.py`)
- [ ] Update `main.py` with dual-server runner and signal handlers
- [ ] Rewrite `sync.py` with `UnixHTTPConnection` (remove TCP/HTTPS/API key)
- [ ] Update `cli.py`:
  - [ ] `cmd_start`: Socket-based "already running" check
  - [ ] `cmd_sync`: Unix socket communication, remove `--api-key`, `--http`, `--port`
  - [ ] `cmd_status`: Unix socket communication, remove `--port`
- [ ] Update tests:
  - [ ] Unit tests for socket path management
  - [ ] Update sync client utils tests
  - [ ] Update E2E tests for socket-based communication
- [ ] Update documentation (AGENTS.md, README.md)

## Open Questions

1. **Socket path override**: Should we support `--socket-path` on the server `start` command as well, or only on client commands?
2. **Socket directory cleanup**: Should we remove the parent directory on shutdown, or leave it? (Leaving it is simpler and harmless)
3. **State endpoint on browser app**: Should browser-facing `/state` return the socket path in the JSON? (Probably not - browsers don't need to know about the admin interface)
