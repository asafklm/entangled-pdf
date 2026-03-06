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

1. Clone or download this repository
2. Install Python dependencies:
```bash
pip install -r requirements.txt
```
3. Install Node.js dependencies (required for PDF.js):
```bash
npm install
```

### Prerequisites for Inverse Search

To use **inverse search** (Shift+Click in PDF → jump to editor), you need:

**For Neovim:**
```bash
pip install neovim-remote
```

**For Vim:** No additional packages needed (uses built-in `+clientserver` feature).

### Shell Setup (One-Time Configuration)

For seamless inverse search, configure your shell to use a fixed editor socket. Add the appropriate configuration to your `~/.bashrc` or `~/.zshrc`:

**For Neovim Users:**
```bash
# PDF Server + Neovim Integration
export NVIM_LISTEN_ADDRESS="/tmp/nvim-${USER}.sock"

# Wrapper function ensures nvim always uses the socket
nvim() {
    command nvim --listen "$NVIM_LISTEN_ADDRESS" "$@"
}

**For Vim Users:**
```bash
# PDF Server + Vim Integration  
export VIM_SERVERNAME="VIM-${USER}"

# Wrapper function ensures vim always uses the servername
vim() {
    command vim --servername "$VIM_SERVERNAME" "$@"
}

**Using UUID-Based Socket (Unique per machine and user):**
```bash
# Generate a unique socket for this machine and user (run once)
echo "export NVIM_LISTEN_ADDRESS=\"/tmp/nvim-$(uuidgen)-${USER}.sock\"" >> ~/.bashrc
# Then reload: source ~/.bashrc
```

> **Note on Multiple Editor Instances:** The fixed socket approach above only supports **one editor instance at a time** for inverse search. If you run multiple nvim/vim instances with the same socket, inverse search may jump to the wrong editor. Experienced users who need multiple instances should devise their own solution (e.g., project-specific sockets or dynamic socket selection).

**Reload your shell:**
```bash
source ~/.bashrc  # or ~/.zshrc
```

### Starting the Server

PdfServer uses two separate tools: `pdf-server` for server management and `sync-remote-pdf` for LaTeX synchronization.

> **Prerequisites**: If using inverse search, ensure you've completed the [Prerequisites](#prerequisites-for-inverse-search) and [Shell Setup](#shell-setup-one-time-configuration) sections above.

**Step 1: Start the server**

```bash
# Basic start (HTTPS mode, no inverse search)
pdf-server start

# Start with inverse search for Neovim (Shift+Click → editor)
# Requires: pip install neovim-remote
pdf-server start --inverse-search-nvim

# Start with inverse search for Vim
pdf-server start --inverse-search-vim

# Start with custom inverse search command
pdf-server start --inverse-search-command "nvr --remote-silent +%{line} %{file}"

# Start on different port
pdf-server start --port 9000

# Start in foreground (for debugging)
pdf-server start --foreground
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

In Neovim with VimTeX:
```lua
-- In your init.lua
vim.g.vimtex_view_method = 'general'
vim.g.vimtex_view_general_viewer = 'sync-remote-pdf'
vim.g.vimtex_view_general_options = '--synctex-forward @line:@col:@tex @pdf'
```

Then use `<leader>lv` to view/forward search.

### Managing the Server

```bash
# Check server status
pdf-server status

# View logs
pdf-server logs
pdf-server logs --follow  # Like tail -f

# Stop the server
pdf-server stop
```

### Manual Forward Search

If you prefer to manually trigger forward search:

```bash
# Load PDF without forward search
sync-remote-pdf document.pdf

# Load PDF with forward search
sync-remote-pdf --synctex-forward "42:5:chapter.tex" document.pdf

# Custom port
sync-remote-pdf --port 9000 document.pdf
```

### Connecting in Browser

1. Start the server with `pdf-server start`
2. Open your browser and navigate to the URL shown (e.g., `https://localhost:8431/view`)
3. Enter the authentication token from the terminal
4. Use `sync-remote-pdf` or VimTeX to load your PDF
5. The PDF will display with page-by-page scrolling support

### Sending Updates via HTTP

You can send position updates to scroll the PDF programmatically:

Using httpie:
```bash
http POST localhost:8431/webhook/update \
  X-API-Key:super-secret-123 \
  page:=2 \
  y:=1000
```

Using curl:
```bash
curl -X POST http://localhost:8431/webhook/update \
  -H "X-API-Key: super-secret-123" \
  -H "Content-Type: application/json" \
  -d '{"page": 2, "y": 1000}'
```

Parameters:
- `page`: Page number to scroll to (required)
- `y`: Vertical position in PDF points (optional, centers on screen if provided)
- `x`: Horizontal position (optional, reserved for future use)

### Environment Variables

- `PDF_SERVER_PORT`: Server port (default: 8431)
- `PDF_SERVER_SECRET`: API key for webhook authentication (default: super-secret-123)
- `PDF_SERVER_HOST`: Server host address (default: 0.0.0.0)

### Project Structure

```
PdfServer/
├── main.py                 # Server entry point
├── bin/
│   ├── pdf-server         # Server lifecycle management (start/stop/status/logs)
│   └── sync-remote-pdf    # LaTeX sync client (forward search only)
├── src/
│   ├── config.py          # Configuration management
│   ├── connection_manager.py  # WebSocket connections
│   ├── logging_config.py    # XDG-compliant logging
│   ├── state.py           # PDF state tracking
│   └── routes/            # API endpoints
│       ├── auth.py        # Token authentication
│       ├── view.py        # HTML viewer
│       ├── pdf.py         # PDF file serving
│       ├── state.py       # State endpoint
│       ├── webhook.py     # SyncTeX webhook
│       ├── websocket.py   # WebSocket endpoint (bidirectional)
│       └── load_pdf.py    # PDF loading API
├── static/                # Frontend assets (TypeScript)
│   ├── viewer.html        # Jinja2 HTML template
│   ├── viewer.ts          # Main viewer with shift+click support
│   ├── token_form.html    # Authentication form
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

# Run specific test file
python -m pytest tests/test_config.py -v

# Run specific test
python -m pytest tests/test_config.py::TestSettings::test_default_values -v
```

### TypeScript Build & Test

```bash
# Install Node.js dependencies
npm install

# Compile TypeScript (generates .js and .d.ts files)
npm run build

# Type check without compiling
npm run typecheck

# Run JavaScript unit tests
npm test

# Run tests in watch mode
npm test -- --watch
```

## Neovim + VimTeX Integration

PdfServer integrates seamlessly with Neovim and VimTeX using the `sync-remote-pdf` CLI tool for forward search, with `pdf-server` managing the server lifecycle.

### Quick Setup (Recommended)

**Step 1: Configure Shell and VimTeX**

First, complete the [Prerequisites](#prerequisites-for-inverse-search) and [Shell Setup](#shell-setup-one-time-configuration) sections above to configure your editor socket.

Then configure VimTeX:

**Neovim** (Lua configuration, e.g., `~/.config/nvim/init.lua`):
```lua
vim.g.vimtex_view_method = 'general'
vim.g.vimtex_view_general_viewer = 'sync-remote-pdf'
vim.g.vimtex_view_general_options = '--synctex-forward @line:@col:@tex @pdf'

-- Optional: Configure port and API key via environment variables
-- vim.env.PDF_SERVER_PORT = '8431'
-- vim.env.PDF_SERVER_SECRET = 'your-secret-key'
```

**Vim** (Vimscript, e.g., `~/.vimrc`):
```vim
let g:vimtex_view_method = 'general'
let g:vimtex_view_general_viewer = 'sync-remote-pdf'
let g:vimtex_view_general_options = '--synctex-forward @line:@col:@tex @pdf'

" Optional: Configure port and API key via environment variables
" let $PDF_SERVER_PORT = '8431'
" let $PDF_SERVER_SECRET = 'your-secret-key'
```

**Step 2: Start the server (one time per session)**

In a terminal, start the server with inverse search enabled:
```bash
pdf-server start --inverse-search-nvim
```

Copy the token and authenticate in your browser.

**Step 3: Work in Neovim**

That's it! Now when you use VimTeX:
- `<leader>ll` - Compile LaTeX document
- `<leader>lv` - View PDF and forward search to cursor position
- Shift+Click in PDF - Jump back to editor (inverse search)

**Note**: The `@line`, `@col`, and `@tex` placeholders are replaced by VimTeX with the current cursor position when you trigger forward search.

### How It Works

When you press `<leader>lv` (VimTeX's default forward search key):

1. **VimTeX** calls: `sync-remote-pdf --synctex-forward line:col:texfile pdffile &`
2. **sync-remote-pdf** checks if pdf_server is running via HTTP `/state`
3. Loads the PDF via `/api/load-pdf` endpoint
4. Sends synctex coordinates to `/webhook/update` endpoint
5. Server converts line:column to PDF coordinates and broadcasts to browser
6. Browser scrolls to position and shows red dot marker
7. For inverse search: Shift+Click triggers `synctex edit` and executes the configured editor command

### Manual Usage

**Start the server:**
```bash
# Start with inverse search for Neovim
pdf-server start --inverse-search-nvim

# Start with custom inverse search
pdf-server start --inverse-search-command "nvr --remote-silent +%{line} %{file}"

# Start on different port
pdf-server start --port 8080

# Foreground mode (for debugging)
pdf-server start --foreground
```

**Load PDF:**
```bash
# Load PDF without forward search
sync-remote-pdf document.pdf

# Load PDF with forward search
sync-remote-pdf --synctex-forward "42:5:chapter.tex" document.pdf

# Custom port
sync-remote-pdf --port 8080 document.pdf
```

**Check status and logs:**
```bash
pdf-server status
pdf-server logs --follow
```

**Stop the server:**
```bash
pdf-server stop
```

### SyncTeX Support

PdfServer supports SyncTeX for precise forward search:

1. Compile your LaTeX document with SyncTeX enabled:
```bash
pdflatex -synctex=1 document.tex
```

2. Forward search automatically converts line:column coordinates to PDF positions

3. The server handles all synctex processing internally

### Inverse Search (Backward Search)

**NEW**: Jump from PDF to editor with Shift+Click!

When enabled, you can click anywhere in the PDF while holding Shift, and your editor will open the corresponding source file at that location.

#### Requirements

**Prerequisites** (must complete before using):
1. **Install nvr** (Neovim only): `pip install neovim-remote`
2. **Configure shell**: Follow the [Shell Setup](#shell-setup-one-time-configuration) section above

**Security requirements**:
- **HTTPS/WSS only**: Inverse search requires secure connections (security feature)
- **Token authentication**: Browser must authenticate with a token from terminal

**Editor support**:
- **Neovim**: Uses `nvr` (via `pip install neovim-remote`)
- **Vim**: Uses built-in `--remote` feature (requires `+clientserver`)

#### Setup

1. Ensure prerequisites are met (see above)

2. Start `pdf-server` with inverse search:
```bash
# For Neovim
pdf-server start --inverse-search-nvim

# For Vim (with +clientserver)
pdf-server start --inverse-search-vim

# Or with custom command
pdf-server start --inverse-search-command "nvr --remote-silent +%{line} %{file}"
```

2. The terminal will display:
```
============================================================
PDF Server Ready (inverse search: nvr)
============================================================
URL:    https://localhost:8431/view
Token:  xJ9mK2pL5nQ8...
============================================================
Copy the token to your browser to enable inverse search
============================================================
```

3. Open the URL in your browser
4. Enter the token when prompted (use clipboard sync for cross-device access)
5. Load your PDF with `sync-remote-pdf document.pdf`
6. **Shift+Click** anywhere in the PDF to jump to the editor!

#### How It Works

When you Shift+Click in the PDF:
1. Browser detects click coordinates
2. Sends page/x/y via authenticated WebSocket
3. Server runs `synctex edit` to convert to file:line
4. Server executes your configured editor command
5. Editor opens file and jumps to line

#### Security Model

- **Token-based auth**: Random 32-byte token (Jupyter-style)
- **HTTPS required**: Inverse search disabled over HTTP
- **Secure cookies**: httpOnly, secure, sameSite=strict
- **Template-based**: Only `%{line}` and `%{file}` interpolated in commands
- **Token regeneration**: New token on each PDF load for security

#### Cross-Device Access

The token authentication enables **secure** cross-device usage:
1. Start server on desktop with `pdf-server start --inverse-search-nvim`
2. Copy token from terminal
3. Use clipboard sync (iCloud, KDE Connect, etc.) to send to tablet/phone
4. Open browser on device, paste token
5. Load PDF with `sync-remote-pdf` or from VimTeX
6. Shift+Click PDF on device → editor jumps on desktop

### Environment Variables

Configure the server and clients via environment variables:

```bash
export PDF_SERVER_PORT=8431        # Server port (used by both pdf-server and sync-remote-pdf)
export PDF_SERVER_SECRET=super-secret-123  # API authentication
```

Or in your editor configuration:

**Neovim** (Lua):
```lua
vim.env.PDF_SERVER_PORT = '8080'
vim.env.PDF_SERVER_SECRET = 'my-secret-key'
```

**Vim** (Vimscript):
```vim
let $PDF_SERVER_PORT = '8080'
let $PDF_SERVER_SECRET = 'my-secret-key'
```

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
   If empty, you haven't completed the [Shell Setup](#shell-setup-one-time-configuration).

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

### Multiple Editor Instances

**Problem**: Inverse search jumps to the wrong editor instance.

**Cause**: The fixed socket approach (e.g., `/tmp/nvim-${USER}.sock`) only supports one editor instance at a time for inverse search.

**Solutions**:
- Close other editor instances
- Use separate terminals for different projects
- Advanced users: Implement project-specific sockets (see [Shell Setup](#shell-setup-one-time-configuration))

### Ghost Neovim Processes

**Problem**: You see unexpected `nvim` processes running after using inverse search.

**Cause**: Old versions of pdf-server used `nvr` without `--nostart`, which would spawn new nvim processes if no server was found.

**Solution**: This is fixed in the current version. Update to the latest version, or clean up manually:
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

## Architecture

- **Backend**: FastAPI with WebSocket support (Python)
- **Frontend**: TypeScript with PDF.js for rendering, compiled to ES2020
- **Build**: TypeScript compiler (tsc) outputs .js alongside .ts sources
- **Protocol**: WebSocket for real-time, HTTP polling as fallback
- **Sync**: Timestamp-based update tracking prevents unnecessary scrolling
- **Testing**: Vitest for TypeScript unit tests with happy-dom environment

## License

Apache 2.0
