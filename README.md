# PdfServer

A FastAPI-based PDF synchronization server with TypeScript frontend that enables real-time PDF viewing across multiple devices with SyncTeX integration for LaTeX forward search from Neovim/VimTeX.

## Main Idea

PdfServer allows you to:
- View PDFs in a web browser with smooth scrolling and high-quality rendering
- Synchronize PDF position across multiple devices (desktop, tablet, phone)
- Jump to specific locations in the PDF from your Neovim editor using SyncTeX
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

### Running the Server

Basic usage:
```bash
python main.py examples/example.pdf
```

With custom port (default is 8431):
```bash
python main.py examples/example.pdf port=8080
```

Or using environment variable:
```bash
export PDF_SERVER_PORT=8080
python main.py examples/example.pdf
```

### Connecting in Browser

1. Start the server (it will listen on all interfaces)
2. Open your browser and navigate to:
   - Local: `http://localhost:8431/view`
   - Network: `http://<your-ip>:8431/view`

The PDF will load and display with page-by-page scrolling support.

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
├── main.py                 # Entry point
├── src/
│   ├── config.py          # Configuration management
│   ├── connection_manager.py  # WebSocket connections
│   ├── state.py           # PDF state tracking
│   └── routes/            # API endpoints
│       ├── view.py        # HTML viewer
│       ├── pdf.py         # PDF file serving
│       ├── state.py       # State endpoint
│       ├── webhook.py     # SyncTeX webhook (enhanced with /synctex)
│       └── websocket.py   # WebSocket endpoint
├── static/                # Frontend assets (TypeScript)
│   ├── viewer.html        # Jinja2 HTML template
│   ├── viewer.ts          # TypeScript viewer (compiled to viewer.js)
│   └── viewer-utils.ts    # Testable utility module
├── VimTeX-integration.lua # Enhanced VimTeX integration script
├── tests/js/              # JavaScript/TypeScript tests
│   ├── viewer-utils.test.ts  # Unit tests
│   └── setup.ts           # Test setup and mocks
├── types/                 # TypeScript type declarations
│   └── pdfjs.d.ts         # PDF.js type definitions
├── tests/                 # Test suite
├── examples/              # Example PDFs
└── requirements.txt       # Dependencies
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

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

PdfServer integrates seamlessly with Neovim and VimTeX for LaTeX forward search with automatic Synctex support.

### Setup

Add to your Neovim configuration (e.g., `[~/.config/nvim/init.lua](~/.config/nvim/init.lua)`):

```lua
-- Load the enhanced PdfServer integration
-- Option 1: Include the provided Lua file
local pdfserver_config = require('path/to/VimTeX-integration')

-- Option 2: Or copy the configuration directly
vim.g.vimtex_view_method = 'general'
vim.g.vimtex_view_general_viewer = 'curl'
vim.g.vimtex_view_general_options = [[
  -X POST
  -H "X-API-Key: super-secret-123"
  -H "Content-Type: application/json"
  -d '{"line": @line, "col": @col, "tex_file": "@tex", "pdf_file": "@pdf"}'
  http://localhost:8431/webhook/synctex
]]

-- Enhanced forward search with automatic Synctex conversion
local function forward_search()
  local line = vim.fn.line('.')
  local col = vim.fn.col('.')
  local file = vim.fn.expand('%:p')
  local pdf = vim.fn.expand('%:r') .. '.pdf'
  
  -- The server now handles synctex conversion automatically
  local curl_cmd = string.format(
    'curl -s -X POST http://localhost:8431/webhook/synctex -H "X-API-Key: super-secret-123" -H "Content-Type: application/json" -d \'{"line": %d, "col": %d, "tex_file": "%s", "pdf_file": "%s"}\' > /dev/null',
    line, col, file, pdf
  )
  os.execute(curl_cmd)
end

-- Map to <leader>lv (VimTeX default forward search)
vim.keymap.set('n', '<leader>lv', forward_search, { buffer = true, desc = 'VimTeX forward search' })

-- Optional: Auto-reload PDF when compilation completes
vim.api.nvim_create_autocmd("User", {
  pattern = "VimtexEventCompileSuccess",
  callback = function()
    local curl_cmd = 'curl -s -X POST http://localhost:8431/webhook/update -H "X-API-Key: super-secret-123" -H "Content-Type: application/json" -d \'{"page": 1}\' > /dev/null'
    os.execute(curl_cmd)
  end,
  desc = "Auto-reload PDF after compilation"
})
```

### Environment Variable Configuration

Set the API key as an environment variable for security:

```bash
export PDF_SERVER_SECRET=your-secret-key
```

Then use it in your Neovim config:

```lua
vim.g.vimtex_view_general_options = [[
  -X POST
  -H "X-API-Key: ]] .. os.getenv("PDF_SERVER_SECRET") .. [["
  -H "Content-Type: application/json"
  -d '{"line": @line, "col": @col, "tex_file": "@tex", "pdf_file": "@pdf"}'
  http://localhost:8431/webhook/synctex
]]
```

### Usage with VimTeX

1. Open a `.tex` file in Neovim
2. Compile with `:VimtexCompile` (or `<leader>ll`)
3. Open the PDF in your browser at `http://<server>:8431/view`
4. Press `<leader>lv` (or your mapped key) to jump to the current cursor position in the PDF

The browser will automatically scroll to the corresponding location and display a red dot marker at the exact position. If the PDF was updated during compilation, it will automatically reload.

### SyncTeX Support

PdfServer supports SyncTeX for precise forward search:

1. Compile your LaTeX document with SyncTeX enabled:
```bash
pdflatex -synctex=1 document.tex
```

2. The server automatically converts line:column coordinates to PDF page and y-coordinate using the `/webhook/synctex` endpoint

3. Use the enhanced synctex integration for more precise positioning:
   - The server handles all synctex processing
   - No need to run synctex manually from VimTeX
   - Automatic PDF reload detection when compilation completes

### Debugging

Use the provided helper functions to debug the integration:

```vim
:SynctexTest    " Test synctex command output
:PdfServerTest  " Test PdfServer connectivity
```

### Advanced Features

- **Automatic PDF Reload**: If synctex fails but the PDF was updated, the browser automatically reloads
- **Silent Failure**: If synctex lookup fails, the operation completes without error
- **Flexible Path Handling**: Accepts both relative and absolute paths for PDF files
- **No Caching**: Each forward search runs fresh synctex for accuracy
- **Single-User Setup**: Designed for individual development workflows

## Features

- **Multi-device sync**: View and control PDF from multiple devices simultaneously
- **WebSocket + HTTP fallback**: Reliable real-time updates with automatic reconnection
- **Smart refocus handling**: Only scrolls to new positions when tab regains focus if there's a new update
- **High-quality rendering**: Optimized canvas rendering for crisp text on all devices
- **Mobile Safari compatible**: Works on iPad and iPhone with smooth scrolling
- **Red dot marker**: Visual indicator shows exact SyncTeX position
- **Environment-based configuration**: Easy deployment with env vars
- **Automatic Synctex conversion**: Server handles line:column to PDF coordinates
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
