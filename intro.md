
# PdfServer

I compile pdf files on my remote server, pdfserver lets me view them in my local browser.
Supports synctex for latex files: **forward sync** (editor → PDF) and **inverse sync** (PDF → editor).

## Main Idea

PdfServer allows you to:
- View PDFs in a web browser with smooth scrolling and high-quality rendering
- Synchronize PDF position across multiple devices (desktop, tablet, phone)
- Jump to specific locations in the PDF from your Neovim editor using SyncTeX (forward search)
- Click in the PDF to jump back to your editor (inverse search with Shift+Click)
- Automatically reconnect and sync when switching back to the browser tab

The server uses WebSockets for real-time updates with automatic fallback to HTTP polling when connections drop. Perfect for LaTeX editing workflows where you want to see your compiled PDF update instantly as you edit.

