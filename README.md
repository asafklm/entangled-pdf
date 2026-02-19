# PdfServer

A FastAPI-based PDF synchronization server that enables real-time PDF viewing across multiple devices with SyncTeX integration for LaTeX forward search from Neovim/VimTeX.

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
2. Install dependencies:
```bash
pip install -r requirements.txt
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
│       ├── webhook.py     # SyncTeX webhook
│       └── websocket.py   # WebSocket endpoint
├── static/                # Frontend assets
│   ├── viewer.html        # HTML template
│   └── viewer.js          # JavaScript viewer
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

## Neovim + VimTeX Integration

PdfServer integrates seamlessly with Neovim and VimTeX for LaTeX forward search.

### Setup

Add to your Neovim configuration (e.g., `~/.config/nvim/init.lua`):

```lua
-- VimTeX configuration with PdfServer SyncTeX support
vim.g.vimtex_view_method = 'general'
vim.g.vimtex_view_general_viewer = 'curl'
vim.g.vimtex_view_general_options = [[
  -X POST
  -H "X-API-Key: super-secret-123"
  -H "Content-Type: application/json"
  -d '{"page": @line, "y": @col}'
  http://localhost:8431/webhook/update
]]

-- Optional: Custom callback for forward search
vim.g.vimtex_callback_progpath = 'nvim'
```

Or use a more robust Lua function:

```lua
local function forward_search()
  local line = vim.fn.line('.')
  local col = vim.fn.col('.')
  local file = vim.fn.expand('%:p')
  
  -- Use synctex to get PDF coordinates
  local cmd = string.format(
    "synctex view -i %d:%d:%s -o %s 2>/dev/null | grep -E 'Page:|y:'",
    line, col, file, vim.fn.expand('%:r') .. '.pdf'
  )
  
  local handle = io.popen(cmd)
  local result = handle:read("*a")
  handle:close()
  
  -- Parse synctex output and send to PdfServer
  local page = result:match("Page:(%d+)")
  local y = result:match("y:(%d+")
  
  if page then
    os.execute(string.format(
      "curl -s -X POST http://localhost:8431/webhook/update " ..
      "-H 'X-API-Key: super-secret-123' " ..
      "-H 'Content-Type: application/json' " ..
      "-d '{\"page\": %s, \"y\": %s}' > /dev/null",
      page, y or "null"
    ))
  end
end

-- Map to <leader>lv (VimTeX default forward search)
vim.keymap.set('n', '<leader>lv', forward_search, { buffer = true, desc = 'VimTeX forward search' })
```

### Usage with VimTeX

1. Open a `.tex` file in Neovim
2. Compile with `:VimtexCompile` (or `<leader>ll`)
3. Open the PDF in your browser at `http://<server>:8431/view`
4. Press `<leader>lv` (or your mapped key) to jump to the current cursor position in the PDF

The browser will automatically scroll to the corresponding location and display a red dot marker at the exact position.

### SyncTeX Support

PdfServer supports SyncTeX for precise forward search:

1. Compile your LaTeX document with SyncTeX enabled:
```bash
pdflatex -synctex=1 document.tex
```

2. Use the synctex command-line tool to get coordinates:
```bash
synctex view -i 42:1:document.tex -o document.pdf
```

3. Send the coordinates to PdfServer via webhook

## Features

- **Multi-device sync**: View and control PDF from multiple devices simultaneously
- **WebSocket + HTTP fallback**: Reliable real-time updates with automatic reconnection
- **Smart refocus handling**: Only scrolls to new positions when tab regains focus if there's a new update
- **High-quality rendering**: Optimized canvas rendering for crisp text on all devices
- **Mobile Safari compatible**: Works on iPad and iPhone with smooth scrolling
- **Red dot marker**: Visual indicator shows exact SyncTeX position
- **Environment-based configuration**: Easy deployment with env vars

## Architecture

- **Backend**: FastAPI with WebSocket support
- **Frontend**: Vanilla JavaScript with PDF.js for rendering
- **Protocol**: WebSocket for real-time, HTTP polling as fallback
- **Sync**: Timestamp-based update tracking prevents unnecessary scrolling

## License

Apache 2.0
