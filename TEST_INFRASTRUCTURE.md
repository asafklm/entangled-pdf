# Test Infrastructure Improvements

This document describes the improvements made to the test infrastructure to prevent zombie process accumulation.

## Changes Made

### 1. Cleanup Utility Script (`bin/pdf-server-test-cleanup`)

A standalone utility script for manually cleaning up orphaned test processes:

```bash
# Show what would be killed (dry run)
./bin/pdf-server-test-cleanup --dry-run

# Clean up with confirmation prompt
./bin/pdf-server-test-cleanup

# Clean up without confirmation
./bin/pdf-server-test-cleanup --force
```

**Features:**
- Safely identifies test processes by:
  - Test certificate patterns (`test.pem`, `test.crt`, etc.)
  - Test port ranges (18080-18200)
  - Test mode flag (`PDF_SERVER_TESTING`)
- **Never kills production servers** (port 8431 with production certificates)
- Graceful termination (SIGTERM) followed by force kill (SIGKILL) if needed

### 2. Process Tracking System (`tests/conftest.py`)

Automatic process tracking and cleanup infrastructure:

- **Tracking file**: `.pytest-pids.json` (in project root)
- Tracks all test server processes with metadata (PID, port, start time)
- Automatically cleans up tracked processes at session end via `atexit`
- Session-scoped fixture auto-cleans stale processes on startup

**Location**: The tracking file is stored in the project directory (not `/tmp`) to avoid permission issues and ensure it's automatically cleaned up with the project.

**Functions exposed:**
- `track_test_process(pid, port, test_id)` - Track a process
- `untrack_test_process(pid)` - Remove from tracking
- `kill_process_tree(pid, timeout)` - Kill process and children
- `find_stale_test_processes()` - Find old zombies

### 3. Improved Fixture Teardown (`tests/test_sync_e2e_subprocess.py`)

The `running_server` fixture now includes:

- Process tracking registration on startup
- Process tree kill with escalating signals (SIGTERM → SIGKILL)
- Exception handling in teardown (prevents fixture errors from masking test failures)
- Automatic untracking even if cleanup fails

**Before (problematic):**
```python
process.terminate()
try:
    process.wait(timeout=5)
except subprocess.TimeoutExpired:
    process.kill()
    process.wait()
```

**After (robust):**
```python
try:
    success = kill_process_tree(process.pid, timeout=5.0)
    if not success:
        os.kill(process.pid, signal.SIGKILL)
except Exception as e:
    print(f"Warning: Error during server teardown: {e}", file=sys.stderr)
finally:
    untrack_test_process(process.pid)
```

## Safety Features

1. **Production Protection**: Cleanup never targets production servers on port 8431
2. **Certificate Detection**: Only kills processes using test certificates
3. **Process Tree Kill**: Uses `psutil` (if available) to kill parent and all children
4. **Timeout Handling**: Graceful 5-second timeout before force kill
5. **Tracking Persistence**: Even if tests crash, processes are tracked for later cleanup

## Usage

### Normal Testing
Just run tests as usual - cleanup is automatic:
```bash
./bin/python -m pytest tests/test_sync_e2e_subprocess.py -v
```

### Manual Cleanup (if needed)
If you notice zombie processes:
```bash
# Check for zombies
./bin/pdf-server-test-cleanup --dry-run

# Kill them
./bin/pdf-server-test-cleanup --force
```

### Session-Level Cleanup
The session-scoped fixture `cleanup_stale_processes` (autouse=True) automatically runs at the start of each test session and cleans up any stale processes from previous interrupted runs.

## Dependencies

The process tree kill function will use `psutil` if available (for killing child processes), but falls back to standard `os.kill()` if not installed.

To install psutil:
```bash
./bin/pip install psutil
```

## Monitoring

You can monitor the process tracking file:
```bash
# View tracked processes (from project root)
cat .pytest-pids.json

# Watch during test run
watch -n 1 cat .pytest-pids.json
```

The file is automatically cleaned up after successful test runs. If it contains entries, those processes may need manual cleanup.

## Future Improvements

Potential future enhancements:
- Use ephemeral ports (port 0) to eliminate port conflicts
- Add CI integration to fail builds if zombies detected
- Add health check before killing to avoid interrupting running tests
