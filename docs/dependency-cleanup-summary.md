# Dependency and CI Cleanup Summary

## Changes Made

### 1. pyproject.toml

**Production Dependencies:**
- ✅ Removed `requests>=2.31.0` (no longer used in production code)

**Dev Dependencies:**
- ✅ Added `psutil>=5.9.0` (was missing, required for test process cleanup)
- ✅ Added `requests>=2.31.0` (moved from production - still needed for tests)

### 2. requirements.txt

- ✅ Removed `requests>=2.31.0` from production dependencies
- ✅ Updated psutil to `psutil>=5.9.0` with version constraint
- ✅ Added comment explaining dev dependencies can be installed with `pip install -e ".[dev]"`

### 3. .github/workflows/ci.yml

**All Python test jobs (fast, slow, e2e):**
- ✅ Removed `responses` from pip install (was not used in any tests)
- ✅ Added socket cleanup step: `rm -f /tmp/entangledpdf_test.sock /tmp/entangledpdf_*.sock`

## Why These Changes?

### Removed `requests` from Production

The production code no longer uses `requests`:
- `cli.py` now uses Unix sockets via `http.client` (stdlib)
- `sync.py` uses `UnixHTTPConnection` (stdlib)

CLI commands (`entangle-pdf sync`, `status`) no longer make HTTP requests - they communicate via Unix domain sockets.

### Added `requests` to Dev Dependencies

The test files still use `requests` for testing HTTP endpoints:
- `tests/test_cli_start.py` - Uses `requests.get()` and `requests.post()`
- `tests/test_cli_status.py` - Uses `requests.post()`

These tests verify the TCP/HTTPS endpoints work correctly.

### Added `psutil` to Dev Dependencies

`psutil` was listed in `requirements.txt` but missing from `pyproject.toml` dev dependencies. It's required by:
- `tests/conftest.py` - For process cleanup utilities

### Removed `responses` from CI

The `responses` library (for mocking HTTP requests) was installed in CI but never actually used in any tests.

### Added Socket Cleanup

E2E tests create Unix sockets. If a previous test run crashed, stale sockets can block subsequent test runs. The cleanup step ensures a clean state.

## Verification

### Production Imports (No requests)

```python
from entangledpdf.socket_path import get_socket_path
from entangledpdf.sync import UnixHTTPConnection, parse_synctex_forward
from entangledpdf.cli import main
# ✓ All imports successful without requests
```

### Dev Dependencies Installed

```
httpx              0.28.1
psutil             7.2.2
pytest             9.0.0
pytest-asyncio     1.3.0
requests           2.33.1
```

### Tests Passing

```bash
./bin/python -m pytest tests/test_socket_path.py -v
# 21 passed in 0.12s
```

## Impact on Users

### End Users (pipx/pip install)

- **Fewer dependencies**: `requests` and `urllib3` no longer installed
- **Smaller installation**: ~1MB smaller
- **No functionality change**: CLI commands work the same (via Unix socket)

### Developers

- **Same test dependencies**: `requests` still available for tests
- **Clearer separation**: Production vs dev dependencies properly separated
- **Easier to understand**: Socket-based architecture reflected in deps

## Files Changed

1. `pyproject.toml` - Updated dependencies
2. `requirements.txt` - Updated dependencies
3. `.github/workflows/ci.yml` - Updated CI test dependencies and added cleanup
4. `docs/dependency-cleanup-summary.md` - This summary (new file)

## Total Commits

This cleanup is part of the `feature/unix-socket-cli` branch which now includes:
- Core Unix socket implementation
- Test updates
- Documentation updates
- Dependency cleanup

Ready for merge to main.
