# Unix Socket Implementation Test Plan

## 1. New Tests Required

### 1.1 Socket Path Management Tests (`tests/test_socket_path.py`)
- [x] **Path resolution order**: `$ENTANGLEDPDF_SOCKET` → `$XDG_RUNTIME_DIR` → `$HOME`
- [x] **Directory creation with permissions**: mode 0700
- [x] **Stale socket detection**: socket exists but no process listening
- [x] **Active server detection**: socket exists and process responding
- [x] **Stale socket cleanup**: remove stale socket successfully
- [x] **Prepare socket path**: integration of directory + stale detection

### 1.2 Unix Socket Client Tests (`tests/test_unix_http_connection.py`)
- [x] **UnixHTTPConnection creation**: initializes with socket path
- [x] **Connection success**: connects to actual Unix socket
- [x] **Connection failure**: raises FileNotFoundError when socket absent
- [x] **HTTP GET request**: send_request returns parsed JSON
- [x] **HTTP POST request**: send_request with JSON data
- [x] **Error handling**: ConnectionRefusedError when server down

### 1.3 Admin App Authentication Tests
- [x] **Unix socket requests skip auth**: `load_pdf` without API key succeeds
- [x] **TCP requests require auth**: `load_pdf` without API key fails with 403
- [x] **Middleware sets state**: `request.state.unix_socket = True`

## 2. Tests to Update

### 2.1 `tests/test_sync_client_utils.py`
- [ ] **Remove**: `TestGetServerUrl` class (replaced by socket path)
- [x] **Keep**: `TestParseSynctexForward` (unchanged)
- [ ] **Update imports**: Remove `get_server_url`, add `get_default_socket_path`

### 2.2 `tests/test_sync_unit.py`
- [ ] **Remove**: `TestCreateSslContext` (no longer needed)
- [ ] **Rewrite**: `TestSendRequest` to use Unix socket instead of HTTPS
- [ ] **Rewrite**: `TestLoadPdf*` classes to use socket path instead of port/api_key
- [ ] **Rewrite**: `TestForwardSearch` to use socket path instead of port/api_key
- [ ] **Rewrite**: `TestMainArgumentParsing` to remove API key requirements
- [ ] **Rewrite**: `TestIntegrationBetweenFunctions` for Unix socket
- [ ] **Remove**: API key related tests (no longer applicable)

### 2.3 `tests/test_sync_e2e_subprocess.py`
- [ ] **Update**: Server fixture to use Unix socket path
- [ ] **Update**: All sync CLI calls to remove `--api-key`, `--port`, `--http` flags
- [ ] **Update**: Assertions to check socket path in output

### 2.4 `tests/test_cli_status.py`
- [ ] **Update**: Use Unix socket for status checks
- [ ] **Remove**: Port-based status checks

### 2.5 `tests/test_cli_start.py`
- [ ] **Update**: Socket-based "already running" detection
- [ ] **Add**: Test for stale socket cleanup

## 3. Tests That Should Still Pass (Unchanged)

- [x] `test_inverse_search.py` - WebSocket auth unchanged
- [x] `test_config.py` - Settings unchanged
- [x] `test_state.py` - State management unchanged
- [x] `test_certs.py` - Certificate generation unchanged
- [x] `test_connection_manager.py` - WebSocket manager unchanged
- [x] `test_logging_sanitizer.py` - Logging unchanged
- [x] `test_websocket_monitor.py` - Monitoring unchanged
- [x] `test_routes_*.py` (except webhook/load_pdf auth tests)

## 4. Running the Tests

```bash
# Run all tests to see initial state
./bin/python -m pytest tests/ -v --tb=short 2>&1 | head -100

# Run specific test files
./bin/python -m pytest tests/test_socket_path.py -v
./bin/python -m pytest tests/test_sync_unit.py -v
./bin/python -m pytest tests/test_sync_client_utils.py -v
```

## 5. Expected Failures

### High Priority (Core Functionality)
1. `test_sync_unit.py::TestSendRequest*` - Old HTTPS/TCP tests
2. `test_sync_unit.py::TestLoadPdf*` - Uses old port/api_key parameters
3. `test_sync_unit.py::TestForwardSearch*` - Uses old port/api_key parameters
4. `test_sync_unit.py::TestMainArgumentParsing*` - Tests API key requirement
5. `test_sync_client_utils.py::TestGetServerUrl` - Removed function

### Medium Priority (Integration)
6. `test_sync_e2e_subprocess.py::*` - E2E tests use old CLI flags
7. `test_cli_status.py::*` - Uses TCP for status
8. `test_cli_start.py::*` - May need socket-related updates

### Low Priority (Edge Cases)
9. Import errors if test files import removed functions
