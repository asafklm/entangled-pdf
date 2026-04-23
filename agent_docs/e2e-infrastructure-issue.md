# E2E Test Infrastructure Issue

**Date:** 2026-04-23  
**Issue:** E2E tests fail to start because they use system Python instead of project venv  
**Fix:** Use project venv Python (`./bin/python`) in `tests/e2e/global-setup.ts`

## Problem Description

The E2E test suite in `tests/e2e/` spawns the PDF server as a subprocess to test against a real running instance. However, the test setup was using system Python (`python3`) which doesn't have the required dependencies installed (uvicorn, fastapi, websockets, etc.).

### Error Message

```
[Server HTTPS stderr] Traceback (most recent call last):
  File "/home/asaf/programming/EntangledPdf/main.py", line 17, in <module>
    import uvicorn
ModuleNotFoundError: No module named 'uvicorn'
```

### Root Cause

In `tests/e2e/global-setup.ts`, line 92:

```typescript
const proc = spawn('python3', args, {
```

This spawns the system `python3` command, but the project uses a virtual environment with all dependencies installed in `./bin/python`.

## Project Setup

The EntangledPdf project uses a Python virtual environment located in the project root:

- **Venv location:** `/home/asaf/programming/EntangledPdf/bin/python`
- **Activation:** Sourced via `./bin/activate` (for shell use)
- **Dependencies:** Listed in `requirements.txt` and `requirements-dev.txt`

### How the project normally runs

According to `AGENTS.md`, the project uses:

```bash
# Python (using project venv)
./bin/python main.py --inverse-search-nvim --foreground
./bin/uvicorn main:app --reload --port 8001
./bin/python -m pytest tests/ -v
```

All commands use `./bin/` executables, not system Python.

## Solution

Changed `tests/e2e/global-setup.ts` to use the project venv Python:

```typescript
// Use project venv Python instead of system python3
// The venv has all dependencies (uvicorn, fastapi, etc.) installed
const venvPython = join(PROJECT_ROOT, 'bin', 'python');
const proc = spawn(venvPython, args, {
```

## Verification

After the fix, E2E tests can successfully:
1. Spawn the HTTPS server with inverse search enabled
2. Spawn the HTTP server for testing non-secure mode
3. Run Playwright tests against the real server

## Related Files

- **Fix location:** `tests/e2e/global-setup.ts` (line 92-96)
- **Test files:** `tests/e2e/*.spec.ts`
- **Project venv:** `./bin/python`

## Impact

This fix enables the E2E test suite to run correctly in CI/CD and local development environments where:
- The project venv is set up (via `install.sh` or manual setup)
- System Python doesn't have the project's dependencies

## Testing the Fix

Run the E2E tests after the fix:

```bash
# Ensure venv is set up
./install.sh  # or manual setup

# Run E2E tests
npm run test:e2e

# Or specific test file
npm run test:e2e -- tests/e2e/inverse-search.spec.ts
```

## Future Considerations

1. **Cross-platform:** The fix uses `join(PROJECT_ROOT, 'bin', 'python')` which works on Unix-like systems (Linux, macOS). Windows would need `join(PROJECT_ROOT, 'Scripts', 'python.exe')`.

2. **Alternative approaches considered:**
   - Modifying PATH env var to include venv bin directory
   - Using a shell wrapper to activate venv
   - Detecting platform and using appropriate path
   
   The current fix is simplest and matches how the rest of the project works.

## Branch

- **Fix branch:** `fix/e2e-venv-path`
- **Target branch:** `main` (to be merged first)
- **Integration branch:** `feature/ctrl_click_inverse_search` (to verify E2E tests pass)
