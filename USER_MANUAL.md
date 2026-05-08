# EntangledPdf User Manual

Complete guide for using EntangledPdf to view and synchronize PDFs with LaTeX editing workflows.

## Table of Contents

1. [Installation](#installation)
2. [Setup](#setup)
3. [Features](#features)
4. [Troubleshooting](#troubleshooting)
5. [Advanced Topics](#advanced-topics)
6. [API Reference](#api-reference)
7. [FAQ](#faq)

---

## Installation

### System Requirements

- **Python**: 3.8 or higher
- **Node.js**: 16 or higher (for PDF.js compilation)
- **Operating System**: Linux, macOS, or Windows with WSL
- **Browser**: Modern browser with WebSocket support (Chrome, Firefox, Safari, Edge)

### Installation Methods

#### Method 1: Install from GitHub with pipx (Recommended for Users)

```bash
# Install pipx first - see https://pipx.pypa.io for installation instructions

# Clone and install
git clone https://github.com/asafklm/entangled-pdf.git
cd entangled-pdf
pipx install .

# Build the frontend (required for PDF rendering)
npm install && npm run build
```

#### Method 2: Install from PyPI

```bash
pip install entangledpdf
```

This installs the `entangle-pdf` command globally.

#### Method 3: Install from Source (For Development)

```bash
# Clone the repository
git clone https://github.com/asafklm/entangled-pdf.git
cd entangled-pdf

# Install Python package
pip install .

# Or for development (editable install)
pip install -e .

# Build the frontend (required for PDF rendering)
npm install && npm run build
```

#### Method 4: Install Dependencies Only (Advanced)

If you prefer not to install the package:

```bash
pip install -r requirements.txt
npm install
npm run build
```

Then use `./bin/entangle-pdf` instead of `entangle-pdf`.

---

## Requirements

### For Forward/Inverse Search (SyncTeX)

To enable forward search (editor → PDF) and inverse search (PDF → editor), you need:

1. **synctex command-line tool** - part of TeX Live
   - See [TeX Live installation](https://www.tug.org/texlive/) for instructions
   - On Ubuntu/Debian: `apt install texlive-extra-utils` (smaller package with synctex)
   - Verify: `synctex --version`

2. **PDF compiled with SyncTeX** - compile with `-synctex=1` flag:
   ```bash
   pdflatex -synctex=1 document.tex
   ```

> **Troubleshooting**: If forward/inverse search fails, check that synctex is installed:
> ```bash
> which synctex
> ```
> If not found, install TeX Live. On Ubuntu/Debian, the `texlive-extra-utils` package provides synctex.

---

## Setup

### 1. API Key Configuration (Required for Browser Access)

EntangledPdf requires an API key for browser access to the PDF viewer. The CLI commands
(`entangle-pdf sync`, `status`) do **not** require an API key—they use Unix socket
authentication instead.

**Generate a secure key:**

```bash
# Add to your shell configuration
echo "export ENTANGLEDPDF_API_KEY=\"$(openssl rand -hex 32)\"" >> ~/.bashrc
source ~/.bashrc
```

**Or use your own password:**

```bash
echo 'export ENTANGLEDPDF_API_KEY="my-secure-password-123"' >> ~/.bashrc
source ~/.bashrc
```

> **Security Note:** Use a long, random key in shared environments. A simple password is acceptable for personal use on a single machine.
> 
> **Note:** The API key is only required for:
> - Browser authentication (viewing PDFs)
> - External tools accessing the TCP/HTTPS endpoints
> 
> CLI commands on the same machine use Unix socket permissions (socket mode 0600) for authentication.

**Verify the key is set:**

```bash
echo $ENTANGLEDPDF_API_KEY
```

### 2. Editor Integration (Optional - for Inverse Search)

To enable **inverse search** (Ctrl+Click in PDF → jump to editor position), configure your editor:

#### Neovim Setup

**Prerequisites:**
```bash
pip install neovim-remote
```

**Shell Configuration** (add to `~/.bashrc` or `~/.zshrc`):
```bash
# PDF Server + Neovim Integration
export NVIM_LISTEN_ADDRESS="/tmp/nvim-${USER}.sock"

# Wrapper function ensures nvim always uses the socket
nvim() {
    command nvim --listen "$NVIM_LISTEN_ADDRESS" "$@"
}
```

**Neovim Configuration** (init.lua):
```lua
vim.g.vimtex_view_method = 'general'
vim.g.vimtex_view_general_viewer = 'entangle-pdf'
vim.g.vimtex_view_general_options = 'sync @pdf @line:@col:@tex'
```

#### Emacs Setup

**Prerequisites:** None - emacsclient is built into Emacs

**Emacs Configuration** (init.el or .emacs):
```elisp
;; Start Emacs server for inverse search
(server-start)
```

**Start Emacs server:**
```bash
# Option 1: Run as daemon (background)
emacs --daemon

# Option 2: Run Emacs normally with (server-start) in your config
```

### 3. SSL Certificates (Optional)

EntangledPdf uses HTTPS by default with self-signed certificates. For production use or to avoid browser warnings, use proper certificates:

**Using your own certificates:**
```bash
entangle-pdf start \
  --ssl-cert /path/to/cert.pem \
  --ssl-key /path/to/key.pem
```

**Installing certificates to default location:**
```bash
python3 -m entangledpdf.certs generate \
  --cert /path/to/cert.pem \
  --key /path/to/key.pem
```

**Example with Let's Encrypt:**
```bash
entangle-pdf start \
  --ssl-cert /etc/letsencrypt/live/yourdomain.com/fullchain.pem \
  --ssl-key /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

**Example with Tailscale:**
```bash
entangle-pdf start --inverse-search-nvim \
  --ssl-cert /etc/ntfy/certs/yourmachine.your-tailnet.ts.net.crt \
  --ssl-key /etc/ntfy/certs/yourmachine.your-tailnet.ts.net.key
```

---

## Features

### Starting the Server

**Basic usage:**
```bash
# HTTPS mode, no inverse search
entangle-pdf start

# With inverse search for Neovim
entangle-pdf start --inverse-search-nvim

# With inverse search for Emacs
entangle-pdf start --inverse-search-emacs

# Custom port
entangle-pdf start --port 9000

# Debug mode (verbose logging)
entangle-pdf start --verbose
```

**On startup, you'll see:**
```
============================================================
PDF Server Ready (inverse search: nvr)
============================================================
URL:    https://localhost:8431/view
Token:  abc123xyz...
============================================================
Copy the token to your browser to enable inverse search
============================================================
```

### Browser Authentication

1. Open the URL shown (e.g., `https://localhost:8431/view`)
2. Enter the token from the terminal
3. You'll see "No PDF loaded" initially - this is normal

### Loading PDFs

**Basic PDF loading:**
```bash
entangle-pdf sync document.pdf
```

**With forward search (jump to specific location):**
```bash
entangle-pdf sync document.pdf 42:5:chapter.tex
```

**Custom socket path (rarely needed):**
```bash
entangle-pdf sync --socket-path /tmp/custom.sock document.pdf
```

**Using VimTeX:**
- Press `<leader>lv` to view PDF and jump to cursor position
- Press `<leader>ll` to compile LaTeX document

> **Note:** No API key is required for `entangle-pdf sync`—it uses Unix socket authentication automatically.

### Connection Status Button

The connection status button appears in the bottom-right corner of the PDF viewer:

#### Button States

| State | Appearance | Meaning | Action on Click |
|-------|-----------|---------|-----------------|
| **Connected** | Green, subtle | WebSocket connected, PDF up to date | Click to view connection details (filename, modification time, last ping) |
| **Reload** | Yellow/Orange, pulsing | New PDF available (different file) | Click to load the new PDF |
| **Reconnect** | Red | WebSocket disconnected | Click to navigate to authentication page |

#### Connection Details Panel

When the button shows "Connected", clicking it reveals:
- Connection status
- Reconnect attempt count
- Last successful ping time
- Current PDF filename
- PDF last modified timestamp

### PDF Switching Behavior

EntangledPdf intelligently handles PDF changes:

**Different PDF file:**
- Shows yellow "Reload" button
- User must click to switch (prevents losing current view)
- Example: Switching from `thesis.pdf` to `appendix.pdf`

**Same PDF modified:**
- Auto-reloads immediately
- No button click needed
- Happens when you recompile the same LaTeX document

**Initial PDF load:**
- Auto-reloads immediately
- No "Reload" button for first PDF

### Keyboard Navigation

The PDF viewer supports Vim-style keyboard shortcuts:

#### Scrolling
- `j` or `↓` - Scroll down
- `k` or `↑` - Scroll up
- `h` or `←` - Scroll left
- `l` or `→` - Scroll right

#### Page Navigation
- `J` or `Page Down` - Next page
- `K` or `Page Up` - Previous page
- `g` - Jump to first page
- `G` - Jump to last page
- `Space` - Scroll one page down (`Shift+Space` for up)

### Inverse Search (PDF → Editor)

Jump from the PDF back to your editor:

**Keyboard:**
- `i` - Trigger inverse search at current scroll position

**Mouse/Touch:**
- `Ctrl+Click` - Jump to clicked location in PDF (Cmd+Click on macOS)
- `Long press/click` (hold ~0.5s) - Jump to held location
- `Long touch` (mobile) - Jump to touched location

**Requirements:**
- Server started with `--inverse-search-nvim` or `--inverse-search-emacs`
- Editor configured with fixed socket (Neovim) or server running (Emacs)
- Browser authenticated with token

### Mobile/Touch Support

- **Smooth scrolling**: Optimized for iPad and iPhone
- **Long touch**: Alternative to Ctrl+Click for inverse search
- **Responsive design**: Works on all screen sizes
- **Touch-friendly**: All controls accessible via touch

### Visual Indicators

**Red Dot Marker:**
- Appears at forward search position
- Shows exact location from SyncTeX
- Auto-fades after a few seconds

**Connection Status:**
- Color indicates connection state
- Pulsing animation for reload needed
- Subtle when connected to avoid distraction

---

## Troubleshooting

### "No PDF loaded" Message

**Problem:** Browser shows "No PDF loaded" after authentication.

**Solution:** This is expected! You need to load a PDF from your editor or CLI:
```bash
entangle-pdf sync your-document.pdf
```

### "nvr: no server found" / Inverse Search Not Working

**Problem:** Ctrl+Click doesn't open your editor.

**Checklist:**

1. **Verify environment variables:**
   ```bash
   echo $NVIM_LISTEN_ADDRESS  # For Neovim
   ```

2. **Check neovim-remote is installed** (Neovim only):
   ```bash
   which nvr
   # If not found: pip install neovim-remote
   ```

3. **Verify editor is running with socket:**
   ```bash
   nvr --serverlist  # For Neovim
   # Should show your $NVIM_LISTEN_ADDRESS
   ```

4. **Reload shell configuration:**
   ```bash
   source ~/.bashrc  # or ~/.zshrc
   ```

5. **Restart the server** after fixing configuration

### Authentication Failed Errors

**Problem:** "Authentication failed (HTTP 403)" when viewing PDFs in browser.

**Causes & Solutions:**

1. **Missing API key:**
   ```bash
   echo $ENTANGLEDPDF_API_KEY
   # If empty, set it: export ENTANGLEDPDF_API_KEY="your-key"
   ```

2. **Server not restarted:** After setting the environment variable:
   ```bash
   # Stop any running server
   pkill -f "entangle-pdf"
   # Restart
   entangle-pdf start --inverse-search-nvim
   ```

> **Note:** CLI commands (`entangle-pdf sync`, `status`) do **not** require the API key.
> They use Unix socket authentication. If you're getting authentication errors from
> CLI commands, check that you own the socket file:
> ```bash
> ls -la $XDG_RUNTIME_DIR/entangledpdf/server.sock
> # Should show your username as owner
> ```

### SSL Certificate Warnings

**Problem:** Browser shows "Your connection is not private" warning.

**Solutions:**

1. **Proceed anyway** (development only):
   - Click "Advanced" → "Proceed to localhost (unsafe)"

2. **Use proper certificates** (recommended):
   ```bash
   entangle-pdf start \
     --ssl-cert /path/to/valid-cert.pem \
     --ssl-key /path/to/valid-key.pem
   ```

3. **Trust self-signed certificate** (one-time setup):
   - Chrome: Click "Not secure" → "Certificate is not valid" → "Install certificate"
   - Follow system prompts to trust the certificate

### Multiple Editor Instances

**Problem:** Inverse search jumps to wrong editor instance.

**Cause:** Fixed socket supports only one editor instance.

**Solutions:**
- Close other editor instances
- Use separate terminals for different projects
- For advanced use: Configure project-specific sockets

### Ghost Neovim Processes

**Problem:** Unexpected `nvim` processes running.

**Solution:** Clean up manually:
```bash
killall nvim  # Warning: closes ALL nvim instances
```

Then restart your editor with the socket configuration.

### PDF Not Updating

**Problem:** Recompiled PDF doesn't show changes.

**Check:**

1. **Check connection status button** - should show yellow "Reload" if different PDF
2. **Check browser console** (F12) for errors
3. **Verify file modification time** changed:
   ```bash
   ls -la your-document.pdf
   ```
4. **Manual reload** - Click the "Reload" button if visible

### WebSocket Disconnections

**Problem:** Connection drops frequently.

**Solutions:**

1. **Check network stability**
2. **Increase timeout** (if behind proxy):
   ```bash
   entangle-pdf start --websocket-timeout 60
   ```
3. **Use HTTP mode** (less secure, for testing only):
   ```bash
   entangle-pdf start --http
   ```

---

## Advanced Topics

### HTTP Mode (Not Recommended)

For local-only development without HTTPS:

```bash
entangle-pdf start --http
```

**Limitations:**
- Inverse search disabled (security requirement)
- No token authentication
- Use only on trusted networks

### Multiple PDF Projects

**Project A (Terminal 1):**
```bash
export ENTANGLEDPDF_PORT=9000
export NVIM_LISTEN_ADDRESS="/tmp/nvim-project-a.sock"
nvim project-a/main.tex
```

**Project B (Terminal 2):**
```bash
export ENTANGLEDPDF_PORT=9001
export NVIM_LISTEN_ADDRESS="/tmp/nvim-project-b.sock"
nvim project-b/main.tex
```

Start separate servers on different ports for each project.

### Custom Webhook Integration

Send PDF updates programmatically:

**Using curl with Unix socket (recommended for local scripts):**
```bash
curl --unix-socket /run/user/$(id -u)/entangledpdf/server.sock \
  -X POST http://localhost/webhook/update \
  -H "Content-Type: application/json" \
  -d '{"page": 2, "y": 1000}'
```

**Using curl with TCP (requires API key):**
```bash
curl -X POST http://localhost:8431/webhook/update \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"page": 2, "y": 1000}'
```

**Using httpie:**
```bash
http POST localhost:8431/webhook/update \
  X-API-Key:your-secret-key \
  page:=2 \
  y:=1000
```

**Using Python (Unix socket):**
```python
import http.client
import json
import socket

# Connect via Unix socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect("/run/user/1000/entangledpdf/server.sock")

conn = http.client.HTTPConnection("localhost")
conn.sock = sock

conn.request(
    "POST", "/webhook/update",
    body=json.dumps({"page": 2, "y": 1000}),
    headers={"Content-Type": "application/json"}
)
response = conn.getresponse()
```

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ENTANGLEDPDF_PORT` | 8431 | Server port (browser access) |
| `ENTANGLEDPDF_API_KEY` | (required) | API key for browser authentication |
| `ENTANGLEDPDF_SOCKET` | `$XDG_RUNTIME_DIR/entangledpdf/server.sock` | Unix socket path for CLI |
| `NVIM_LISTEN_ADDRESS` | (none) | Neovim socket path (for inverse search) |
| `ENTANGLEDPDF_TEST_PORT` | 18080 | Port for E2E tests |
| `ENTANGLEDPDF_TEST_SOCKET` | `/tmp/entangledpdf_test.sock` | Socket path for E2E tests |

---

## Socket Configuration

### How CLI Commands Find the Server

The `entangle-pdf sync` and `status` commands communicate with the server through a Unix domain socket instead of TCP. Both the server and CLI commands automatically use the same socket path, so they "just work" without any configuration.

### Default Socket Path Resolution

The socket path is resolved automatically (in order of priority):

1. **`$ENTANGLEDPDF_SOCKET`** environment variable (if set)
2. **`$XDG_RUNTIME_DIR/entangledpdf/server.sock`** (default on most Linux systems with systemd/logind, typically `/run/user/<uid>/entangledpdf/server.sock`)
3. **`$HOME/.local/run/entangledpdf/server.sock`** (fallback for systems without XDG)

To see the actual socket path being used:
```bash
entangle-pdf status
```

### Custom Socket Path

Override the default socket path when running multiple servers as the same user:

**Terminal 1 (Project A):**
```bash
export ENTANGLEDPDF_SOCKET=/tmp/server-project-a.sock
export ENTANGLEDPDF_PORT=9000
entangle-pdf start --inverse-search-nvim
```

**Terminal 2 (Project B):**
```bash
export ENTANGLEDPDF_SOCKET=/tmp/server-project-b.sock
export ENTANGLEDPDF_PORT=9001
entangle-pdf start --inverse-search-nvim
```

**Load PDF to Project A:**
```bash
entangle-pdf sync --socket-path /tmp/server-project-a.sock document-a.pdf
```

### Socket Permissions

The socket file is created with mode `0600` (only the owner can read/write). This provides authentication — only the user who started the server can connect to it. This is why CLI commands don't require an API key.

### Multiple Users on Same Machine

Each user gets their own socket path automatically because:
- `$XDG_RUNTIME_DIR` is user-specific (e.g., `/run/user/1000` vs `/run/user/1001`)
- `$HOME` is different for each user

Users cannot interfere with each other's servers because they cannot connect to each other's sockets.

---

## API Reference

### WebSocket Protocol

Messages are JSON objects with an `action` field.

#### Server → Client Messages

**Reload PDF:**
```json
{
  "action": "reload",
  "pdf_file": "document.pdf",
  "pdf_mtime": 1234567890.123
}
```

**SyncTeX Position:**
```json
{
  "action": "synctex",
  "page": 1,
  "x": 100.5,
  "y": 200.5,
  "last_sync_time": 1234567890123,
  "pdf_file": "document.pdf",
  "pdf_mtime": 1234567890.123
}
```

**Error:**
```json
{
  "action": "error",
  "message": "Error description"
}
```

#### Client → Server Messages

**Ping (keepalive):**
```json
{
  "action": "ping",
  "timestamp": 1234567890123
}
```

**Inverse Search:**
```json
{
  "action": "inverse_search",
  "page": 1,
  "y": 200.5,
  "x": 100.5
}
```

### HTTP Endpoints

#### GET /state

Returns current PDF state.

**Authentication:**
- **TCP/HTTPS**: No authentication required
- **Unix socket**: No authentication (filesystem permissions)

**Response:**
```json
{
  "page": 1,
  "y": 500.0,
  "x": 100.0,
  "last_sync_time": 1234567890123,
  "pdf_file": "/path/to/document.pdf",
  "pdf_basename": "document.pdf",
  "pdf_mtime": 1234567890.123,
  "pdf_loaded": true,
  "https": true,
  "inverse_search_enabled": true,
  "websocket_token": "abc123..."  // Only from localhost
}
```

#### POST /api/load-pdf

Load a new PDF file.

**Authentication:**
- **TCP/HTTPS**: `X-API-Key` header required
- **Unix socket**: No authentication (filesystem permissions)

**Headers (TCP/HTTPS only):**
- `X-API-Key`: Your API key
- `Content-Type: application/json`

**Body:**
```json
{
  "pdf_path": "/path/to/document.pdf"
}
```

**Response:**
```json
{
  "status": "success",
  "pdf_file": "/path/to/document.pdf",
  "filename": "document.pdf",
  "changed": true
}
```

#### POST /webhook/update

Send forward search update.

**Authentication:**
- **TCP/HTTPS**: `X-API-Key` header required
- **Unix socket**: No authentication (filesystem permissions)

**Headers (TCP/HTTPS only):**
- `X-API-Key`: Your API key
- `Content-Type: application/json`

**Body:**
```json
{
  "line": 42,
  "col": 5,
  "tex_file": "/path/to/chapter.tex",
  "pdf_file": "/path/to/document.pdf"
}
```

**Response:**
```json
{
  "status": "success",
  "page": 1,
  "y": 500.0,
  "x": 100.0
}
```

---

## FAQ

### Q: Why does the browser show "No PDF loaded"?

**A:** This is normal! You need to load a PDF from your editor or CLI. The browser viewer waits for a PDF to be loaded via `entangle-pdf sync`.

### Q: Can I use EntangledPdf with Emacs?

**A:** Yes! EntangledPdf supports Emacs with `--inverse-search-emacs`. Just ensure Emacs is running with `(server-start)` in your config or start with `emacs --daemon`.

### Q: How do I view the PDF on my iPad?

**A:** 
1. Start the server on your computer
2. Find your computer's IP address: `hostname -I`
3. Open `https://<ip-address>:8431/view` on your iPad
4. Enter the token shown in the server terminal
5. Load the PDF from your editor

### Q: Why does the connection status button show "Reload"?

**A:** A "Reload" button (yellow/orange) means a different PDF file is available than what's currently displayed. Click it to switch to the new PDF. This prevents accidentally losing your current view.

### Q: Can I use HTTP instead of HTTPS?

**A:** Yes, but inverse search will be disabled for security reasons:
```bash
entangle-pdf start --http
```

### Q: How do I debug connection issues?

**A:** 
1. Start server with verbose logging: `entangle-pdf start --verbose`
2. Open browser console (F12) to see WebSocket messages
3. Check the connection status button in the PDF viewer
4. Verify `ENTANGLEDPDF_API_KEY` is set on both sides

### Q: Does EntangledPdf support multiple simultaneous PDFs?

**A:** One PDF at a time per server instance. Start multiple servers on different ports for multiple PDFs.

### Q: Why doesn't `entangle-pdf sync` require an API key?

**A:** CLI commands use Unix domain sockets for communication instead of TCP. The socket file has permissions mode 0600, meaning only the owner can connect. This provides authentication via filesystem permissions, so no API key is needed for local CLI commands. The API key is only required for browser access (TCP/HTTPS endpoints).

### Q: Where is the Unix socket file located?

**A:** Default locations (in order of preference):
1. `$ENTANGLEDPDF_SOCKET` environment variable (if set)
2. `$XDG_RUNTIME_DIR/entangledpdf/server.sock` (typically `/run/user/<uid>/entangledpdf/server.sock`)
3. `$HOME/.local/run/entangledpdf/server.sock` (fallback)

Use `entangle-pdf status` to see the actual socket path being used.

### Q: What happens if I edit the PDF while viewing?

**A:** If it's the same PDF file (just modified), it will auto-reload. If it's a different PDF file, you'll see a "Reload" button to click.

### Q: Can I customize the keyboard shortcuts?

**A:** Not currently. Shortcuts are hardcoded to Vim-style navigation. Custom keybindings may be added in future versions.

### Q: Is my PDF content secure?

**A:** Yes:
- PDFs are served over HTTPS (encrypted)
- Token authentication required for viewing
- No PDF content is exposed through the public `/state` endpoint (only metadata like page number)
- API key required for all modifications

### Q: How do I completely reset the server?

**A:**
```bash
entangle-pdf stop
# Kill any remaining processes
killall -f "entangle-pdf"
# Restart
entangle-pdf start --inverse-search-nvim
```

### Q: Where are the log files?

**A:** 
- Server logs: Check terminal output (use `--verbose` for more detail)
- Browser logs: Open browser console (F12)
- Test logs: In `test-results/` directory after running E2E tests

---

## Getting Help

- **GitHub Issues:** Report bugs and feature requests
- **Documentation:** This manual and README.md
- **Code Reference:** AGENTS.md for developers

## License

MIT License - See LICENSE file for details.
