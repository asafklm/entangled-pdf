# EntangledPdf

A FastAPI-based PDF synchronization server with TypeScript frontend that enables real-time PDF viewing across multiple devices with SyncTeX integration for LaTeX **forward search** (editor → PDF) and **inverse search** (PDF → editor via Shift+Click).

## Main Idea

EntangledPdf allows you to:
- View PDFs in a web browser with smooth scrolling and high-quality rendering
- Synchronize PDF position across multiple devices (desktop, tablet, phone)
- Jump to specific locations in the PDF from your Neovim editor using SyncTeX (forward search)
- Click in the PDF to jump back to your editor (inverse search with Shift+Click)
- Automatically reconnect and sync when switching back to the browser tab

The server uses WebSockets for real-time updates with automatic fallback to HTTP polling when connections drop. Perfect for LaTeX editing workflows where you want to see your compiled PDF update instantly as you edit.

## Quick Start

### Installation

#### Option 1: Install from GitHub (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/entangledpdf.git
cd entangledpdf

# Install the package (includes Python dependencies)
pip install .

# Or for development (editable install)
pip install -e .
```

#### Option 2: Install Python Dependencies Only

If you prefer not to install the package:

```bash
pip install -r requirements.txt
```

#### Node.js Dependencies (Required for PDF.js)

```bash
npm install
npm run build  # Compile TypeScript to JavaScript
```

> **Note:** After `pip install .`, the command `entangle-pdf` will be available in your PATH. If using the development approach (without pip install), use `./bin/entangle-pdf` instead.

### Setup

After installation, complete the required setup and optional editor configuration.

#### 1. API Key (Required)

The API key controls who can trigger PDF updates and forward search. Anyone with network 
access to the server who knows this key can load PDFs and initiate forward sync. 
The intended use is that your TeX editor and the EntangledPdf server share the same 
key via the `ENTANGLEDPDF_API_KEY` environment variable—this ensures only your 
authorized editor can control the PDF viewer, preventing updates from third parties.

Generate a unique API key and add it to your shell:

```bash
# Generate a secure random key and add to ~/.bashrc (or ~/.zshrc)
entangle-pdf generate-api-key --shell >> ~/.bashrc

# Reload your shell
source ~/.bashrc
```

Alternatively, generate just the key:
```bash
# Copy the key and add it manually
entangle-pdf generate-api-key
# Then add to your shell: export ENTANGLEDPDF_API_KEY="<paste-key-here>"
```

Or use your own password:
```bash
# Use your own password (must be unique and hard to guess)
echo 'export ENTANGLEDPDF_API_KEY="my-unique-password-123"' >> ~/.bashrc
source ~/.bashrc
```

> **Security:** Use a long, random key in shared environments. A simple password is fine for personal use on a single machine.

#### 2. SSL Certificates (Required)

EntangledPdf uses HTTPS by default with self-signed certificates. Generate them before first use:

```bash
python -m entangledpdf.certs generate
```

This creates certificates in `~/.local/share/pdf_server/certs/`. You'll see a browser warning on first access—click "Advanced" → "Accept" to proceed.

To use your own certificates instead, see [SSL Certificates](#ssl-certificates) below.

#### 3. VimTeX Setup (Optional - for Inverse Search)

To use **inverse search** (Shift+Click in PDF → jump to editor) with Vim/Neovim, 
configure your editor socket. Note: Other editors and LaTeX plugins can also 
integrate with EntangledPdf using the `entangle-pdf sync` command (see Manual Commands below).

**Prerequisites:**
- **Neovim**: `pip install neovim-remote`
- **Vim**: No additional packages needed

**Shell Configuration:**

Add to your `~/.bashrc` or `~/.zshrc`:

**For Neovim:**
```bash
# PDF Server + Neovim Integration
export NVIM_LISTEN_ADDRESS="/tmp/nvim-${USER}.sock"

# Wrapper function ensures nvim always uses the socket
nvim() {
    command nvim --listen "$NVIM_LISTEN_ADDRESS" "$@"
}
```

**For Vim:**
```bash
# PDF Server + Vim Integration  
export VIM_SERVERNAME="VIM-${USER}"

# Wrapper function ensures vim always uses the servername
vim() {
    command vim --servername "$VIM_SERVERNAME" "$@"
}
```

**Editor Configuration:**

**Neovim** (init.lua):
```lua
vim.g.vimtex_view_method = 'general'
vim.g.vimtex_view_general_viewer = 'entangle-pdf'
vim.g.vimtex_view_general_options = 'sync @pdf @line:@col:@tex'
```

**Vim** (.vimrc):
```vim
let g:vimtex_view_method = 'general'
let g:vimtex_view_general_viewer = 'entangle-pdf'
let g:vimtex_view_general_options = 'sync @pdf @line:@col:@tex'
```

Then reload your shell:
```bash
source ~/.bashrc  # or ~/.zshrc
```

> **Note:** The fixed socket approach supports only one editor instance at a time. If you need multiple instances, use project-specific sockets.

### Starting the Server

**Step 1: Start the server**

```bash
# Basic start (HTTPS mode, no inverse search)
entangle-pdf start

# Start with inverse search for Neovim
entangle-pdf start --inverse-search-nvim

# Start with inverse search for Vim
entangle-pdf start --inverse-search-vim

# Start on different port
entangle-pdf start --port 9000

# Start in foreground (for debugging)
entangle-pdf start --verbose
```

When you start the server, you'll see:
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

**About the Token:** This browser authentication token is separate from your API key. 
The token prevents others on your network from viewing your PDFs or performing 
inverse search (jumping to your editor). Unlike the API key (which persists via 
your shell configuration), this token is regenerated every time the server starts 
for security reasons.

**Step 2: Authenticate in browser**

1. Open the URL shown (e.g., `https://localhost:8431/view`)
2. Enter the token from the terminal
3. You'll see "No PDF loaded" - this is expected!

**Step 3: Test with a sample PDF**

Before using VimTeX, verify the setup works by manually loading a PDF:

```bash
# Load an example PDF from the repository
entangle-pdf sync examples/example.pdf
```

You should now see the PDF in your browser. This confirms the server, API key, 
and browser are all configured correctly. If this works but VimTeX doesn't, 
you'll know the issue is in your editor configuration.

> **For other editors/plugins:** You can integrate by calling `entangle-pdf sync <pdf-file>` 
> after compilation. See [Manual Commands](#manual-commands) for details.

**Step 4: Work in your editor**

In Neovim/Vim with VimTeX:
- `<leader>ll` - Compile LaTeX document
- `<leader>lv` - View PDF and forward search to cursor position
- Shift+Click in PDF - Jump back to editor (inverse search)

### SSL Certificates

EntangledPdf uses HTTPS by default with self-signed certificates. To use your own certificates:

```bash
# Specify certificates at runtime
entangle-pdf start --ssl-cert /path/to/cert.pem --ssl-key /path/to/key.pem

# Or install certificates to default location
python -m entangledpdf.certs generate --cert /path/to/cert.pem --key /path/to/key.pem
```

**Example with Tailscale certificates:**
```bash
entangle-pdf start --inverse-search-nvim \
  --ssl-cert /etc/ntfy/certs/elul.asymptote-cirius.ts.net.crt \
  --ssl-key /etc/ntfy/certs/elul.asymptote-cirius.ts.net.key
```

You can obtain certificates from [Let's Encrypt](https://letsencrypt.org/) or [Tailscale HTTPS](https://tailscale.com/kb/1153/https/).

#### HTTP Mode (Not Recommended)

For local-only development without HTTPS:
```bash
entangle-pdf start --http
```

Note: Inverse search is disabled in HTTP mode for security.

## Usage Guide

### PDF Viewer Controls

The browser-based PDF viewer supports keyboard navigation (Vim-style) and multiple methods for inverse search.

#### Navigation

**Scrolling:**
- `j` or `↓` - Scroll down
- `k` or `↑` - Scroll up  
- `h` or `←` - Scroll left
- `l` or `→` - Scroll right

**Page Navigation:**
- `J` or `Page Down` - Next page
- `K` or `Page Up` - Previous page
- `g` - Jump to first page
- `G` - Jump to last page
- `Space` - Scroll one page down (`Shift+Space` for up)

#### Inverse Search (Jump PDF → Editor)

Trigger inverse search at the current position to jump to the corresponding source code in your editor:

**Keyboard:**
- `i` - Trigger inverse search at the current scroll position

**Mouse/Touch:**
- `Shift+Click` on PDF - Jump to clicked location
- `Long press/click` (hold ~0.5 seconds) - Jump to held location  
- `Long touch` (mobile) - Jump to touched location

> **Note:** Inverse search requires server to be started with `--inverse-search-nvim` or `--inverse-search-vim`, and your editor must be configured with a fixed socket (see [Setup](#setup)).

### VimTeX Integration

EntangledPdf integrates seamlessly with VimTeX using the `entangle-pdf sync` CLI tool.

**How It Works:**

When you press `<leader>lv`:
1. VimTeX calls: `entangle-pdf sync @pdf @line:@col:@tex`
2. Server converts line:column to PDF coordinates via SyncTeX
3. Browser scrolls to position and shows red dot marker
4. When you Shift+Click in the PDF, browser sends coordinates to server
5. Server runs `synctex edit` to convert to file:line and opens your editor

### Manual Commands

**Loading PDFs:**

```bash
# Load PDF without forward search
entangle-pdf sync document.pdf

# Load PDF with forward search (line:column:texfile)
entangle-pdf sync document.pdf 42:5:chapter.tex

# Custom port
entangle-pdf sync document.pdf --port 9000

# Custom API key (if not using env var)
entangle-pdf sync document.pdf --api-key "your-secret-key"
```

**Server Management:**

```bash
# Check server status
entangle-pdf status

# Generate API key
entangle-pdf generate-api-key --shell
```

### Inverse Search (Backward Search)

Jump from PDF to editor with Shift+Click.

**Requirements:**
- Server started with inverse search enabled (`--inverse-search-nvim` or `--inverse-search-vim`)
- Editor configured with fixed socket (see [Setup](#setup))
- Browser authenticated with token from server startup

**Security:**
- Token-based authentication (Jupyter-style)
- HTTPS required (inverse search disabled over HTTP)
- Secure cookies with httpOnly, secure, sameSite=strict
- Token regenerates on server restart

### Sending Updates via HTTP

You can send position updates programmatically:

Using httpie:
```bash
http POST localhost:8431/webhook/update \
  X-API-Key:your-secret-key \
  page:=2 \
  y:=1000
```

Using curl:
```bash
curl -X POST http://localhost:8431/webhook/update \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"page": 2, "y": 1000}'
```

Parameters:
- `page`: Page number to scroll to (required)
- `y`: Vertical position in PDF points (optional, centers on screen if provided)
- `x`: Horizontal position (optional, reserved for future use)

### Environment Variables

- `ENTANGLEDPDF_PORT`: Server port (default: 8431, used by both server and client)
- `ENTANGLEDPDF_API_KEY`: API key for authentication (required)
- `NVIM_LISTEN_ADDRESS`: Neovim socket path (for inverse search)
- `VIM_SERVERNAME`: Vim server name (for inverse search)

### Security

**Authentication Model:**

| Endpoint | Auth Required | Data Protected | Notes |
|----------|---------------|----------------|-------|
| `/view`, `/get-pdf` | `pdf_token` cookie | PDF content | Token set after auth form |
| WebSocket (`/ws`) | `?token=` param | Inverse search | Same token as cookie |
| `/state` | None | Page position, sync time | **Public metadata** (see below) |
| `/webhook/update` | `X-API-Key` header | SyncTeX updates | Server-to-server only |
| `/api/load-pdf` | `X-API-Key` header | PDF loading | Server-to-server only |

**Public Metadata (`/state`):**

The `/state` endpoint is intentionally unauthenticated. It returns:
- Current page number and Y position
- Last sync timestamp  
- PDF filename
- Whether a PDF is loaded

**This is not a security vulnerability** because:
- No PDF content is exposed (position data is meaningless without the PDF)
- The endpoint is read-only (cannot modify state)
- Forward sync already requires `X-API-Key` from trusted clients
- Position metadata is similar to "which page is open" - not sensitive in most contexts

**Token Lifecycle:**

- Token is generated per-server-instance (not per-PDF)
- Token changes when server restarts
- Re-authentication required after restart for inverse search
- API key (forward sync) persists across restarts via `ENTANGLEDPDF_API_KEY` env var

**Secure Defaults:**

- HTTPS/WSS required for inverse search (HTTP mode disables it)
- Secure cookies: `httpOnly`, `secure`, `sameSite=strict`
- Tokens are cryptographically random (256-bit entropy)
- API key authentication for server-to-server communication

### "nvr: no server found" / Inverse search not working

**Problem**: Shift+Click in PDF doesn't open your editor, or you see "no server found" errors.

**Check these items:**

1. **Verify shell configuration**:
   ```bash
   echo $NVIM_LISTEN_ADDRESS  # For Neovim
   # or
   echo $VIM_SERVERNAME       # For Vim
   ```
   If empty, you haven't completed the [VimTeX Setup](#3-vimtex-setup-optional---for-inverse-search).

2. **Check that nvr is installed** (Neovim only):
   ```bash
   which nvr
   # If not found: pip install neovim-remote
   ```

3. **Verify editor is running with the socket**:
   ```bash
   nvr --serverlist  # For Neovim
   # Should show your $NVIM_LISTEN_ADDRESS value
   ```

4. **Reload your shell**:
   ```bash
   source ~/.bashrc  # or ~/.zshrc
   ```

### Authentication Failed Errors

**Problem**: You see "Authentication failed" when loading PDFs.

**Solution**: Ensure the same `ENTANGLEDPDF_API_KEY` is used on both server and client:
1. Check server has the key: `echo $ENTANGLEDPDF_API_KEY`
2. Check client has the key: `echo $ENTANGLEDPDF_API_KEY`
3. Restart the server after setting the environment variable

### Multiple Editor Instances

**Problem**: Inverse search jumps to the wrong editor instance.

**Cause**: The fixed socket approach only supports one editor instance at a time.

**Solutions**:
- Close other editor instances
- Use separate terminals for different projects
- Advanced users: Implement project-specific sockets

### Ghost Neovim Processes

**Problem**: You see unexpected `nvim` processes running.

**Solution**: Clean up manually:
```bash
killall nvim  # Warning: closes ALL nvim instances
```

## Features

- **Multi-device sync**: View and control PDF from multiple devices simultaneously
- **Inverse search**: Shift+Click PDF to jump to source code in editor (HTTPS/WSS only)
- **Token-based auth**: Secure Jupyter-style authentication for inverse search
- **WebSocket + HTTP fallback**: Reliable real-time updates with automatic reconnection
- **Smart refocus handling**: Only scrolls to new positions when tab regains focus if there's a new update
- **High-quality rendering**: Optimized canvas rendering for crisp text on all devices
- **Mobile Safari compatible**: Works on iPad and iPhone with smooth scrolling
- **Red dot marker**: Visual indicator shows exact SyncTeX position
- **Environment-based configuration**: Easy deployment with env vars
- **Automatic Synctex conversion**: Server handles line:column to PDF coordinates and vice versa
- **Auto PDF reload**: Detects PDF updates and refreshes browser automatically
- **Silent error handling**: Gracefully handles synctex failures without disrupting workflow
- **Flexible path handling**: Accepts both relative and absolute PDF paths

## Development

### Project Structure

```
EntangledPdf/
├── main.py                 # Server entry point
├── bin/
│   └── entangle-pdf         # Server lifecycle management
├── entangledpdf/
│   ├── config.py          # Configuration management
│   ├── connection_manager.py  # WebSocket connections
│   ├── state.py           # PDF state tracking
│   └── routes/            # API endpoints
├── static/                # Frontend assets (TypeScript)
│   ├── viewer.html        # Jinja2 HTML template
│   ├── viewer.ts          # Main viewer
│   └── viewer.js          # Compiled JavaScript
├── tests/                 # Test suite
├── examples/              # Example PDFs
└── requirements.txt       # Dependencies
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx responses

# Run all Python tests
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/test_config.py -v                              # Configuration tests
python -m pytest tests/test_sync_unit.py -v                           # sync.py unit tests  
python -m pytest tests/test_sync_e2e_subprocess.py -v                 # E2E tests with real server
python -m pytest tests/test_sync_client_utils.py -v                   # entangle-pdf sync client tests

# Run specific test
python -m pytest tests/test_config.py::TestSettings::test_default_values -v

# E2E tests use port 18080 by default. Override with:
ENTANGLEDPDF_TEST_PORT=28080 python -m pytest tests/test_sync_e2e_subprocess.py -v
```

### TypeScript Build & Test

```bash
# Install Node.js dependencies
npm install

# Compile TypeScript
npm run build

# Type check without compiling
npm run typecheck

# Run JavaScript unit tests (Vitest)
npm test

# Run tests in watch mode
npm test -- --watch

# Run Playwright E2E tests (browser tests)
npm run test:e2e

# Run E2E tests with UI
npm run test:e2e:ui

# Run E2E tests in debug mode
npm run test:e2e:debug
```

### Architecture

- **Backend**: FastAPI with WebSocket support (Python)
- **Frontend**: TypeScript with PDF.js for rendering, compiled to ES2020
- **Build**: TypeScript compiler (tsc) outputs .js alongside .ts sources
- **Protocol**: WebSocket for real-time, HTTP polling as fallback
- **Sync**: Timestamp-based update tracking prevents unnecessary scrolling
- **Testing**: Vitest for TypeScript unit tests, Playwright for E2E browser tests

## License

MIT License
