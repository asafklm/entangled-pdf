"""Root pytest configuration for tests.

Provides fixtures that are shared across all test files.
"""

import atexit
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set default API key for tests
os.environ.setdefault("PDF_SERVER_API_KEY", "test-api-key-for-testing")

# Process tracking configuration
# Store in project directory (not /tmp) to avoid permission issues
PROJECT_ROOT = Path(__file__).parent.parent
TEST_PID_FILE = PROJECT_ROOT / ".pytest-pids.json"
TEST_PORT_RANGE = range(18080, 18200)


def load_tracked_processes() -> Dict[str, dict]:
    """Load tracked test processes from file."""
    if not TEST_PID_FILE.exists():
        return {}
    try:
        with open(TEST_PID_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_tracked_processes(processes: Dict[str, dict]):
    """Save tracked test processes to file."""
    try:
        with open(TEST_PID_FILE, "w") as f:
            json.dump(processes, f, indent=2)
    except IOError as e:
        print(f"Warning: Could not save process tracking file: {e}", file=sys.stderr)


def track_test_process(pid: int, port: int, test_id: str):
    """Track a test server process for cleanup."""
    processes = load_tracked_processes()
    processes[str(pid)] = {
        "port": port,
        "test_id": test_id,
        "started_at": time.time(),
        "cmd": f"main.py --port {port}",
    }
    save_tracked_processes(processes)


def untrack_test_process(pid: int):
    """Remove a process from tracking."""
    processes = load_tracked_processes()
    processes.pop(str(pid), None)
    save_tracked_processes(processes)


def is_process_alive(pid: int) -> bool:
    """Check if a process is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def kill_process_tree(pid: int, timeout: float = 5.0) -> bool:
    """Kill a process and all its children with escalating signals."""
    import psutil
    
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # First, try graceful termination (SIGTERM)
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        
        try:
            parent.terminate()
        except psutil.NoSuchProcess:
            return True
        
        # Wait for graceful termination
        gone, alive = psutil.wait_procs(children + [parent], timeout=timeout)
        
        # If still alive, force kill (SIGKILL)
        for proc in alive:
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass
        
        # Final wait
        if alive:
            psutil.wait_procs(alive, timeout=1)
        
        return not is_process_alive(pid)
        
    except psutil.NoSuchProcess:
        return True
    except ImportError:
        # Fallback without psutil - just kill the main process
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(timeout)
            if is_process_alive(pid):
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)
            return not is_process_alive(pid)
        except (OSError, ProcessLookupError):
            return True


def cleanup_tracked_processes():
    """Clean up all tracked test processes. Called at session end."""
    processes = load_tracked_processes()
    if not processes:
        return
    
    print(f"\nCleaning up {len(processes)} tracked test process(es)...")
    failed = []
    
    for pid_str, info in list(processes.items()):
        pid = int(pid_str)
        if is_process_alive(pid):
            print(f"  Terminating PID {pid} (port {info.get('port', '?')})...")
            if not kill_process_tree(pid, timeout=3.0):
                failed.append(pid)
        else:
            # Already dead, just clean up tracking
            pass
    
    # Clear the tracking file
    if TEST_PID_FILE.exists():
        TEST_PID_FILE.unlink()
    
    if failed:
        print(f"  Warning: Failed to kill {len(failed)} process(es): {failed}")


# Register cleanup on exit
atexit.register(cleanup_tracked_processes)


def find_stale_test_processes() -> List[int]:
    """Find orphaned test processes from previous runs."""
    stale_pids = []
    
    # Check tracked processes file
    tracked = load_tracked_processes()
    for pid_str, info in tracked.items():
        pid = int(pid_str)
        if is_process_alive(pid):
            # Check if it's old (older than 5 minutes)
            started = info.get("started_at", 0)
            if time.time() - started > 300:  # 5 minutes
                stale_pids.append(pid)
    
    # Also scan for processes using test certificates
    try:
        result = subprocess.run(
            ["pgrep", "-f", r"main\.py.*--ssl-cert.*test\.(pem|crt)"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    try:
                        pid = int(line.strip())
                        if pid not in stale_pids:
                            stale_pids.append(pid)
                    except ValueError:
                        pass
    except Exception:
        pass
    
    return stale_pids


@pytest.fixture(scope="session", autouse=True)
def cleanup_stale_processes():
    """Automatically clean up stale test processes at session start."""
    stale = find_stale_test_processes()
    if stale:
        print(f"\nFound {len(stale)} stale test process(es) from previous runs, cleaning up...")
        for pid in stale:
            kill_process_tree(pid, timeout=2.0)
    yield
    # Cleanup at session end is handled by atexit


@pytest.fixture(scope="function")
def real_test_client():
    """Create a test client using the real static directory.
    
    This fixture is for tests that need to verify the actual HTML template
    and static files, not the minimal test fixtures.
    """
    from main import create_app
    from entangledpdf.config import Settings, settings as global_settings
    from entangledpdf.state import pdf_state
    from entangledpdf.connection_manager import manager
    
    project_root = Path(__file__).parent.parent
    static_dir = project_root / "static"
    
    if not static_dir.exists():
        pytest.skip("static directory not found")
    
    # Create a test PDF file
    test_pdf = project_root / "test_document.pdf"
    test_pdf.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
    
    # Create settings with real static directory
    settings = Settings(
        pdf_file=test_pdf,
        port=18080,
        api_key="test-api-key-for-testing",
        static_dir=static_dir
    )
    
    # Patch the global settings before creating the app
    with patch("entangledpdf.config.settings", settings):
        app = create_app()
        
        with patch("entangledpdf.routes.view.get_settings", return_value=settings):
            with patch("entangledpdf.routes.pdf.get_settings", return_value=settings):
                with patch("entangledpdf.routes.state.get_settings", return_value=settings):
                    with TestClient(app) as client:
                        yield client
    
    # Cleanup
    if test_pdf.exists():
        test_pdf.unlink()


# Import fixtures from integration tests
from tests.integration.conftest import (
    test_app,
    test_client,
    test_settings,
    temp_pdf_file,
    reset_state,
    reset_connections,
    mock_websocket_client,
)
