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

### Using the CLI Client

The `remote_pdf` CLI tool provides Zathura-compatible integration for VimTeX:

```bash
# Open PDF (auto-starts server if needed)
bin/remote_pdf examples/example.pdf

# Open with forward search
bin/remote_pdf --synctex-forward "42:5:chapter.tex" document.pdf

# Custom port
bin/remote_pdf --port 8080 document.pdf
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
├── bin/
│   └── remote_pdf           # CLI client for VimTeX integration (Zathura-compatible)
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

PdfServer integrates seamlessly with Neovim and VimTeX using the `remote_pdf` CLI tool (Zathura-compatible interface).

### Quick Setup (Recommended)

Simply configure VimTeX to use `remote_pdf` as the general viewer:

```lua
-- Add to your Neovim configuration (e.g., ~/.config/nvim/init.lua)
vim.g.vimtex_view_method = 'general'
vim.g.vimtex_view_general_viewer = 'remote_pdf'

-- Optional: Configure port and API key via environment variables
-- vim.env.PDF_SERVER_PORT = '8431'
-- vim.env.PDF_SERVER_SECRET = 'your-secret-key'
```

That's it! The `remote_pdf` tool handles everything automatically:
- **First compile**: Starts pdf_server automatically when you first view a PDF
- **Forward search**: Standard `<leader>lv` jumps to cursor position in PDF
- **PDF reload**: Automatic reload when the PDF file is modified
- **Server lifecycle**: Automatic server management (start, restart, shutdown)

### How It Works

When you press `<leader>lv` (VimTeX's default forward search key):

1. **VimTeX** calls: `remote_pdf --synctex-forward line:col:texfile pdffile &`
2. **remote_pdf** checks if pdf_server is running via HTTP `/state`
3. If not running: starts pdf_server automatically
4. If serving different PDF: restarts server with new PDF
5. Sends synctex coordinates to `/webhook/update` endpoint
6. Server converts line:column to PDF coordinates and broadcasts to browser
7. Browser scrolls to position and shows red dot marker

### Manual Usage (Without VimTeX)

You can also use `remote_pdf` standalone:

```bash
# Open PDF (auto-starts server if needed)
remote_pdf document.pdf &

# Open with forward search
remote_pdf --synctex-forward "42:5:chapter.tex" document.pdf &

# Custom port
remote_pdf --port 8080 document.pdf &

# Verbose output (for debugging)
remote_pdf -v --synctex-forward "10:1:main.tex" main.pdf
```

### SyncTeX Support

PdfServer supports SyncTeX for precise forward search:

1. Compile your LaTeX document with SyncTeX enabled:
```bash
pdflatex -synctex=1 document.tex
```

2. Forward search automatically converts line:column coordinates to PDF positions

3. The server handles all synctex processing internally

### Environment Variables

Configure `remote_pdf` and the server via environment variables:

```bash
export PDF_SERVER_PORT=8431        # Server port
export PDF_SERVER_SECRET=super-secret-123  # API authentication
```

Or set in your Neovim init.lua:

```lua
vim.env.PDF_SERVER_PORT = '8080'
vim.env.PDF_SERVER_SECRET = 'my-secret-key'
```

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
