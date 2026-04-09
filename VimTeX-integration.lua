-- Enhanced VimTeX integration with EntangledPdf SyncTeX support
-- Add this to your Neovim config (init.lua) for the new remote_pdf CLI tool.
-- This replaces the old 248-line Lua integration with a simple 2-line configuration.

-- Simple configuration for remote_pdf CLI tool
vim.g.vimtex_view_method = 'general'
vim.g.vimtex_view_general_viewer = 'remote_pdf'

-- Optional: Set environment variables for configuration
-- vim.env.PDF_SERVER_PORT = '8431'
-- vim.env.PDF_SERVER_SECRET = 'your-secret-key'

-- That's it! VimTex will handle the rest:
-- - First compile: entangle-pdf start (if not already running)
-- - <leader>lv: Standard VimTeX forward search works via entangle-pdf sync
-- - PDF reload: Automatic when file is modified
-- - Server lifecycle: Managed by entangle-pdf command

-- NOTE: Make sure entangle-pdf is in your PATH. It's installed via pip.
