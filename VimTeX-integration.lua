-- Enhanced VimTeX integration with PdfServer SyncTeX support
-- Add this to your Neovim config (init.lua)

-- Configuration
-- Set the path to the PdfServer directory (containing main.py)
-- Default: ~/PdfServer
vim.g.pdf_server_path = vim.g.pdf_server_path or vim.fn.expand('~/PdfServer')

-- Read port from environment or use default
local pdf_server_port = os.getenv('PDF_SERVER_PORT') or '8431'

-- Configuration with automatic PDF reload detection
vim.g.vimtex_view_method = 'general'
vim.g.vimtex_view_general_viewer = 'curl'
vim.g.vimtex_view_general_options = string.format([[
  -X POST
  -H "X-API-Key: super-secret-123"
  -H "Content-Type: application/json"
  -d '{"line": @line, "col": @col, "tex_file": "@tex", "pdf_file": "@pdf"}'
  http://localhost:%s/webhook/synctex
]], pdf_server_port)

-- Get the PDF file path for the current TeX file
local function get_current_pdf_path()
  return vim.fn.expand('%:r') .. '.pdf'
end

-- Check if the PDF server is running and get the current PDF it's serving
-- Returns: pdf_path (string) if running, nil if not running
local function get_server_pdf()
  local curl_cmd = string.format(
    'curl -s --max-time 2 http://localhost:%s/current-pdf 2>/dev/null',
    pdf_server_port
  )
  
  local handle = io.popen(curl_cmd)
  if not handle then
    return nil
  end
  
  local result = handle:read('*a')
  handle:close()
  
  if result and result ~= '' then
    -- Parse JSON response to extract pdf_file
    local pdf_file = result:match('"pdf_file"%s*:%s*"([^"]+)"')
    if pdf_file then
      -- URL decode the path (handle escaped characters)
      pdf_file = pdf_file:gsub('\\/', '/'):gsub('%%(%x%x)', function(h)
        return string.char(tonumber(h, 16))
      end)
      return pdf_file
    end
  end
  
  return nil
end

-- Start the PDF server for the given PDF file
-- Returns: job_id (number) if successful, nil if failed
local function start_pdf_server(pdf_path)
  local server_path = vim.g.pdf_server_path
  local python_exe = server_path .. '/bin/python'
  local main_py = server_path .. '/main.py'
  
  -- Check if server files exist
  if vim.fn.filereadable(main_py) == 0 then
    vim.notify('PdfServer not found at: ' .. server_path, vim.log.levels.ERROR)
    return nil
  end
  
  -- Build the command
  local cmd = { python_exe, main_py, pdf_path, 'port=' .. pdf_server_port }
  
  -- Start the server as a detached job
  local job_id = vim.fn.jobstart(cmd, {
    detach = true,
    cwd = server_path,
    on_stdout = function(_, data) end,  -- Suppress output
    on_stderr = function(_, data) end,  -- Suppress errors
  })
  
  if job_id <= 0 then
    vim.notify('Failed to start PdfServer', vim.log.levels.ERROR)
    return nil
  end
  
  -- Store job ID for potential cleanup
  vim.g.pdf_server_job_id = job_id
  
  vim.notify('PdfServer started for: ' .. vim.fn.fnamemodify(pdf_path, ':t'), vim.log.levels.INFO)
  
  -- Give the server a moment to start
  vim.wait(1000, function() return true end)
  
  return job_id
end

-- Stop the currently running PDF server
-- Returns: true if successful, false otherwise
local function stop_pdf_server()
  local curl_cmd = string.format(
    'curl -s -X POST http://localhost:%s/webhook/shutdown -H "X-API-Key: super-secret-123" 2>/dev/null',
    pdf_server_port
  )
  
  local result = os.execute(curl_cmd)
  
  if result == 0 then
    vim.notify('PdfServer shutdown initiated', vim.log.levels.INFO)
    -- Give the server time to shut down
    vim.wait(1500, function() return true end)
    return true
  else
    vim.notify('Failed to stop PdfServer', vim.log.levels.WARN)
    return false
  end
end

-- Main function to manage server on compilation success
-- This is called by the VimtexEventCompileSuccess autocmd
local function manage_server_on_compile()
  local expected_pdf = get_current_pdf_path()
  local server_pdf = get_server_pdf()
  
  if not server_pdf then
    -- Server is not running - start it
    vim.notify('PdfServer not running, starting...', vim.log.levels.INFO)
    start_pdf_server(expected_pdf)
  elseif server_pdf ~= expected_pdf then
    -- Server is running a different PDF - restart it
    vim.notify('PdfServer serving different file, restarting...', vim.log.levels.INFO)
    if stop_pdf_server() then
      start_pdf_server(expected_pdf)
    end
  else
    -- Server is running the same PDF - just reload
    local curl_cmd = string.format(
      'curl -s -X POST http://localhost:%s/webhook/update -H "X-API-Key: super-secret-123" -H "Content-Type: application/json" -d \'{"page": 1}\' > /dev/null',
      pdf_server_port
    )
    os.execute(curl_cmd)
    vim.notify('PDF reloaded', vim.log.levels.INFO)
  end
end

-- Enhanced forward search function with synctex conversion
local function forward_search()
  local line = vim.fn.line('.')
  local col = vim.fn.col('.')
  local file = vim.fn.expand('%:p')
  local pdf = get_current_pdf_path()
  
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
      'curl -s -X POST http://localhost:%s/webhook/synctex -H "X-API-Key: super-secret-123" -H "Content-Type: application/json" -d \'{"line": %d, "col": %d, "tex_file": "%s", "pdf_file": "%s"}\' > /dev/null',
      pdf_server_port, line, col, file, pdf
    )
    os.execute(curl_cmd)
  end
end

-- Map to VimTeX forward search
vim.keymap.set('n', '<leader>lv', forward_search, { buffer = true, desc = 'VimTeX forward search' })

-- Auto-reload PDF and manage server when compilation completes
vim.api.nvim_create_autocmd("User", {
  pattern = "VimtexEventCompileSuccess",
  callback = function()
    manage_server_on_compile()
  end,
  desc = "Auto-start/restart PdfServer and reload PDF after compilation"
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
  local pdf = get_current_pdf_path()
  
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
  let port = $PDF_SERVER_PORT
  if empty(port)
    let port = '8431'
  endif
  let cmd = 'curl -s -X POST http://localhost:' . port . '/webhook/synctex -H "X-API-Key: super-secret-123" -H "Content-Type: application/json" -d \'' . '{"line": ' . line . ', "col": ' . col . ', "tex_file": "' . file . '", "pdf_file": "' . pdf . '"}\'' . ' > /dev/null'
  echo cmd
  call system(cmd)
endfunction

function! PdfServerStatus()
  lua << EOF
  local server_pdf = get_server_pdf()
  if server_pdf then
    print("PdfServer running, serving: " .. server_pdf)
  else
    print("PdfServer not running")
  end
EOF
endfunction
