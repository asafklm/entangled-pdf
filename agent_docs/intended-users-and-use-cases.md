# Project Context: Intended Users and Use Cases

## The Core Insight

**EntangledPdf is a specialized tool for a specific, uncommon workflow.** It is NOT a general-purpose PDF viewer replacement.

### The Intended User

EntangledPdf is specifically designed for:
- Users who write LaTeX on a **remote, headless server** (not locally)
- Users who want to view the compiled PDF in a **web browser** (not a native PDF viewer)
- Users who need **SyncTeX support** to maintain their position in the PDF across compilations

This is a tiny minority of LaTeX users. Most people fall into one of these categories:
1. **Local editors**: TeXShop, TeXMaker, LyX users, or Vim/Neovim/Emacs users with local PDF viewers like Zathura, Skim, or Okular
2. **Online editors**: Overleaf users who get a full browser-based LaTeX environment with built-in PDF viewer

### Why Does This Exist?

When editing LaTeX on a remote server via SSH, common approaches for viewing PDFs include:
- **SFTP**: Download PDF after every compilation (tedious)
- **Remote filesystem + local viewer**: Mount remote dir locally, use native PDF viewer (complex setup)
- **Simple HTTP server**: Run `python -m http.server` on the remote server and view in browser

The HTTP server approach is simple and works, but has one problem: **you lose your position in the PDF after every reload**. EntangledPdf solves this by adding SyncTeX support—when you forward search from your editor, the browser scrolls to the exact location.

### Multi-Device "Feature"

The README previously mentioned "synchronizing across multiple devices (desktop, tablet, phone)" but this is **NOT the intended use case**. The multi-device capability is simply an architectural byproduct of using WebSockets and a web browser. The intended user is editing on ONE remote server and viewing on ONE browser.

The multi-device capability happens to work, but it is not why the tool exists.

### Editor Agnosticism

While the README shows VimTeX integration examples, EntangledPdf is **editor-agnostic**. It provides a CLI tool (`entangle-pdf sync`) that any editor or LaTeX plugin can call. The examples use Neovim/Vim because that's what the author uses, but the tool works with Emacs, VSCode, or any editor that can shell out to a command.

## Technical Architecture Notes

### WebSocket Broadcasting

The `ConnectionManager` class broadcasts updates to all connected WebSocket clients. This enables the multi-device behavior, but in the intended use case, there's typically only ONE connected client.

### State Management

The `PDFState` class tracks:
- `current_page`: Current page number
- `current_y`: Vertical position in PDF points
- `last_sync_time`: Timestamp of last forward sync
- `pdf_file`: Path to currently loaded PDF
- `websocket_token`: Security token for browser authentication

This state persists across reconnections and is broadcast to all clients.

## Key Misconceptions to Avoid

1. **NOT a local PDF viewer replacement**: Users working locally should use Zathura, Skim, Okular, or their editor's built-in viewer
2. **NOT a multi-device sync tool**: While it technically works, this is not the intended use case
3. **NOT a general LaTeX editing environment**: Unlike Overleaf, this is just a PDF viewer with SyncTeX
4. **NOT a collaboration tool**: No multi-user editing, commenting, or version control

## Honest Positioning

EntangledPdf fills a narrow gap:
- Simpler than setting up a remote filesystem mount
- More functional than `python -m http.server` (SyncTeX support)
- Lighter than self-hosting Overleaf Community Edition
- More flexible than being locked into a specific editor's PDF viewer

It is a **specialized solution for a specialized workflow**.
