# PdfServer

A FastAPI-based PDF synchronization server with TypeScript frontend that enables real-time PDF viewing across multiple devices with SyncTeX integration for LaTeX **forward search** (editor → PDF) and **inverse search** (PDF → editor via Shift+Click).

## Main Idea

PdfServer allows you to:
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
git clone https://github.com/yourusername/pdfserver.git
cd pdfserver

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

> **Note:** After `pip install .`, the command `pdf-server` will be available in your PATH. If using the development approach (without pip install), use `./bin/pdf-server` instead.

### Setup

After installation, complete the required setup and optional editor configuration.

#### 1. API Key (Required)

Generate a unique API key and add it to your shell:

```bash
# Generate a secure random key and add to ~/.bashrc (or ~/.zshrc)
echo "export PDF_SERVER_API_KEY=\"$(openssl rand -hex 32)\"" >> ~/.bashrc

# Reload your shell
source ~/.bashrc
```

Alternatively, you can use your own password:
```bash
# Use your own password (must be unique and hard to guess)
echo 'export PDF_SERVER_API_KEY="my-unique-password-123"' >> ~/.bashrc
source ~/.bashrc
```

> **Security:** Use a long, random key in shared environments. A simple password is fine for personal use on a single machine.

#### 2. Editor Setup (Optional - for Inverse Search)

To use **inverse search** (Shift+Click in PDF → jump to editor), configure your editor socket:

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
vim.g.vimtex_view_general_viewer = 'pdf-server'
vim.g.vimtex_view_general_options = 'sync @pdf @line:@col:@tex'
```

**Vim** (.vimrc):
```vim
let g:vimtex_view_method = 'general'
let g:vimtex_view_general_viewer = 'pdf-server'
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
pdf-server start

# Start with inverse search for Neovim
pdf-server start --inverse-search-nvim

# Start with inverse search for Vim
pdf-server start --inverse-search-vim

# Start on different port
pdf-server start --port 9000

# Start in foreground (for debugging)
pdf-server start --verbose
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

**Step 2: Authenticate in browser**

1. Open the URL shown (e.g., `https://localhost:8431/view`)
2. Enter the token from the terminal
3. You'll see "No PDF loaded" - this is expected!

**Step 3: Work in your editor**

In Neovim/Vim with VimTeX:
- `<leader>ll` - Compile LaTeX document
- `<leader>lv` - View PDF and forward search to cursor position
- Shift+Click in PDF - Jump back to editor (inverse search)

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

PdfServer integrates seamlessly with VimTeX using the `pdf-server sync` CLI tool.

**How It Works:**

When you press `<leader>lv`:
1. VimTeX calls: `pdf-server sync @pdf @line:@col:@tex`
2. Server converts line:column to PDF coordinates via SyncTeX
3. Browser scrolls to position and shows red dot marker
4. When you Shift+Click in the PDF, browser sends coordinates to server
5. Server runs `synctex edit` to convert to file:line and opens your editor

### Manual Commands

**Loading PDFs:**

```bash
# Load PDF without forward search
pdf-server sync document.pdf

# Load PDF with forward search (line:column:texfile)
pdf-server sync document.pdf 42:5:chapter.tex

# Custom port
pdf-server sync document.pdf --port 9000

# Custom API key (if not using env var)
pdf-server sync document.pdf --api-key "your-secret-key"
```

**Server Management:**

```bash
# Check server status
pdf-server status
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
- Token regenerates on each PDF load

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

- `PDF_SERVER_PORT`: Server port (default: 8431, used by both server and client)
- `PDF_SERVER_API_KEY`: API key for authentication (required)
- `NVIM_LISTEN_ADDRESS`: Neovim socket path (for inverse search)
- `VIM_SERVERNAME`: Vim server name (for inverse search)

## Troubleshooting

### "nvr: no server found" / Inverse search not working

**Problem**: Shift+Click in PDF doesn't open your editor, or you see "no server found" errors.

**Check these items:**

1. **Verify shell configuration**:
   ```bash
   echo $NVIM_LISTEN_ADDRESS  # For Neovim
   # or
   echo $VIM_SERVERNAME       # For Vim
   ```
   If empty, you haven't completed the [Editor Setup](#2-editor-setup-optional---for-inverse-search).

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

**Solution**: Ensure the same `PDF_SERVER_API_KEY` is used on both server and client:
1. Check server has the key: `echo $PDF_SERVER_API_KEY`
2. Check client has the key: `echo $PDF_SERVER_API_KEY`
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
PdfServer/
├── main.py                 # Server entry point
├── bin/
│   └── pdf-server         # Server lifecycle management
├── pdfserver/
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

# Run all tests
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/test_config.py -v                              # Configuration tests
python -m pytest tests/test_sync_unit.py -v                           # sync.py unit tests  
python -m pytest tests/test_sync_e2e_subprocess.py -v                 # E2E tests with real server
python -m pytest tests/test_sync_client_utils.py -v                   # pdf-server sync client tests

# Run specific test
python -m pytest tests/test_config.py::TestSettings::test_default_values -v

# E2E tests use port 18080 by default. Override with:
PDF_SERVER_TEST_PORT=28080 python -m pytest tests/test_sync_e2e_subprocess.py -v
```

### TypeScript Build & Test

```bash
# Install Node.js dependencies
npm install

# Compile TypeScript
npm run build

# Type check without compiling
npm run typecheck

# Run JavaScript unit tests
npm test

# Run tests in watch mode
npm test -- --watch
```

### Architecture

- **Backend**: FastAPI with WebSocket support (Python)
- **Frontend**: TypeScript with PDF.js for rendering, compiled to ES2020
- **Build**: TypeScript compiler (tsc) outputs .js alongside .ts sources
- **Protocol**: WebSocket for real-time, HTTP polling as fallback
- **Sync**: Timestamp-based update tracking prevents unnecessary scrolling
- **Testing**: Vitest for TypeScript unit tests with happy-dom environment

## License

Apache 2.0
