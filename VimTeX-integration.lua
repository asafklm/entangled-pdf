-- Enhanced VimTeX integration with PdfServer SyncTeX support
-- Add this to your Neovim config (init.lua)

-- Configuration with automatic PDF reload detection
vim.g.vimtex_view_method = 'general'
vim.g.vimtex_view_general_viewer = 'curl'
vim.g.vimtex_view_general_options = [[
  -X POST
  -H "X-API-Key: super-secret-123"
  -H "Content-Type: application/json"
  -d '{"line": @line, "col": @col, "tex_file": "@tex", "pdf_file": "@pdf"}'
  http://localhost:8431/webhook/synctex
]]

-- Enhanced forward search function with synctex conversion
local function forward_search()
  local line = vim.fn.line('.')
  local col = vim.fn.col('.')
  local file = vim.fn.expand('%:p')
  local pdf = vim.fn.expand('%:r') .. '.pdf'
  
  -- Run synctex to get PDF coordinates
  local cmd = string.format(
    "synctex view -i %d:%d:%s -o %s 2>/dev/null",
    line, col, file, pdf
  )
  
  local handle = io.popen(cmd)
  local result = handle:read("*a")
  handle:close()
  
  -- Parse synctex output
  local page = result:match("Page:(%d+)")
  local y = result:match("y:(%d+%.?%d*)")
  
  if page then
    -- Send to PdfServer
    local curl_cmd = string.format(
      'curl -s -X POST http://localhost:8431/webhook/synctex -H "X-API-Key: super-secret-123" -H "Content-Type: application/json" -d \'{"line": %d, "col": %d, "tex_file": "%s", "pdf_file": "%s"}\' > /dev/null',
      line, col, file, pdf
    )
    os.execute(curl_cmd)
  end
end

-- Map to VimTeX forward search
vim.keymap.set('n', '<leader>lv', forward_search, { buffer = true, desc = 'VimTeX forward search' })

-- Optional: Auto-reload PDF when compilation completes
vim.api.nvim_create_autocmd("User", {
  pattern = "VimtexEventCompileSuccess",
  callback = function()
    -- Trigger PDF reload in PdfServer
    local curl_cmd = 'curl -s -X POST http://localhost:8431/webhook/update -H "X-API-Key: super-secret-123" -H "Content-Type: application/json" -d \'{"page": 1}\' > /dev/null'
    os.execute(curl_cmd)
  end,
  desc = "Auto-reload PDF after compilation"
})

-- Error handling and logging
local function handle_synctex_error(err)
  print("VimTeX forward search error:", err)
  print("Make sure synctex is installed and your document was compiled with -synctex=1")
end

-- Debug mode for development
local function debug_synctex()
  print("Testing synctex command...")
  local line = vim.fn.line('.')
  local col = vim.fn.col('.')
  local file = vim.fn.expand('%:p')
  local pdf = vim.fn.expand('%:r') .. '.pdf'
  
  local cmd = string.format(
    "synctex view -i %d:%d:%s -o %s",
    line, col, file, pdf
  )
  
  print("Running:", cmd)
  os.execute(cmd)
end

-- Helper functions for development
function! SynctexTest()
  let line = line('.')
  let col = col('.')
  let file = expand('%:p')
  let pdf = expand('%:r') . '.pdf'
  let cmd = 'synctex view -i ' . line . ':' . col . ':' . file . ' -o ' . pdf
  echo cmd
  call system(cmd)
endfunction

function! PdfServerTest()
  let line = line('.')
  let col = col('.')
  let file = expand('%:p')
  let pdf = expand('%:r') . '.pdf'
  let cmd = 'curl -s -X POST http://localhost:8431/webhook/synctex -H "X-API-Key: super-secret-123" -H "Content-Type: application/json" -d \'{"line": ' . line . ', "col": ' . col . ', "tex_file": "' . file . '", "pdf_file": "' . pdf . '"}\' > /dev/null'
  echo cmd
  call system(cmd)
endfunction