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

## Setup

### 1. API Key Configuration (Required)

EntangledPdf requires an API key for authentication between the server and client.

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

**Verify the key is set:**

```bash
echo $ENTANGLEDPDF_API_KEY
```

### 2. Editor Integration (Optional - for Inverse Search)

To enable **inverse search** (Shift+Click in PDF → jump to editor position), configure your editor:

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

#### Vim Setup

**Shell Configuration** (add to `~/.bashrc` or `~/.zshrc`):
```bash
# PDF Server + Vim Integration  
export VIM_SERVERNAME="VIM-${USER}"

# Wrapper function ensures vim always uses the servername
vim() {
    command vim --servername "$VIM_SERVERNAME" "$@"
}
```

**Vim Configuration** (.vimrc):
```vim
let g:vimtex_view_method = 'general'
let g:vimtex_view_general_viewer = 'entangle-pdf'
let g:vimtex_view_general_options = 'sync @pdf @line:@col:@tex'
```

**Reload your shell:**
```bash
source ~/.bashrc  # or ~/.zshrc
```

> **Note:** The fixed socket approach supports only one editor instance at a time.

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

# With inverse search for Vim
entangle-pdf start --inverse-search-vim

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

**Custom port:**
```bash
entangle-pdf sync document.pdf --port 9000
```

**Using VimTeX:**
- Press `<leader>lv` to view PDF and jump to cursor position
- Press `<leader>ll` to compile LaTeX document

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
- `Shift+Click` - Jump to clicked location in PDF
- `Long press/click` (hold ~0.5s) - Jump to held location
- `Long touch` (mobile) - Jump to touched location

**Requirements:**
- Server started with `--inverse-search-nvim` or `--inverse-search-vim`
- Editor configured with fixed socket
- Browser authenticated with token

### Mobile/Touch Support

- **Smooth scrolling**: Optimized for iPad and iPhone
- **Long touch**: Alternative to Shift+Click for inverse search
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

**Problem:** Shift+Click doesn't open your editor.

**Checklist:**

1. **Verify environment variables:**
   ```bash
   echo $NVIM_LISTEN_ADDRESS  # For Neovim
   echo $VIM_SERVERNAME       # For Vim
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

**Problem:** "Authentication failed (HTTP 403)" when loading PDFs.

**Causes & Solutions:**

1. **Missing API key:**
   ```bash
   echo $ENTANGLEDPDF_API_KEY
   # If empty, set it: export ENTANGLEDPDF_API_KEY="your-key"
   ```

2. **Mismatched keys:** Server and client must use the same key
   - Check server: `entangle-pdf status`
   - Check client: `echo $ENTANGLEDPDF_API_KEY`

3. **Server not restarted:** After setting the environment variable:
   ```bash
   entangle-pdf stop
   entangle-pdf start --inverse-search-nvim
   ```

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

**Using httpie:**
```bash
http POST localhost:8431/webhook/update \
  X-API-Key:your-secret-key \
  page:=2 \
  y:=1000
```

**Using curl:**
```bash
curl -X POST http://localhost:8431/webhook/update \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"page": 2, "y": 1000}'
```

**Using Python:**
```python
import requests

response = requests.post(
    "http://localhost:8431/webhook/update",
    headers={"X-API-Key": "your-secret-key"},
    json={"page": 2, "y": 1000}
)
```

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ENTANGLEDPDF_PORT` | 8431 | Server port |
| `ENTANGLEDPDF_API_KEY` | (required) | API key for authentication |
| `NVIM_LISTEN_ADDRESS` | (none) | Neovim socket path |
| `VIM_SERVERNAME` | (none) | Vim server name |
| `ENTANGLEDPDF_TEST_PORT` | 18080 | Port for E2E tests |

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

Returns current PDF state (public, no authentication required).

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

**Headers:**
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

**Headers:**
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

**A:** Not directly. EntangledPdf currently supports Neovim and Vim. Emacs support would require implementing a new inverse search command handler.

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
