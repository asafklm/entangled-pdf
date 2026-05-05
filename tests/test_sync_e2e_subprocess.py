"""End-to-end integration tests for entangle-pdf sync CLI with real server subprocess.

These tests spawn actual entangle-pdf and entangle-pdf sync processes to test real-world
usage without any mocking. Uses Unix domain sockets for CLI-server communication.

Environment Variables:
    ENTANGLEDPDF_TEST_SOCKET: Override default test socket path
    ENTANGLEDPDF_TEST_DIR: Override temp directory for test artifacts

Example:
    ENTANGLEDPDF_TEST_SOCKET=/tmp/test.sock pytest tests/test_sync_e2e_subprocess.py -v
"""

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

from entangledpdf.certs import generate_self_signed_cert
from entangledpdf.sync import (
    forward_search,
    load_pdf,
    parse_synctex_forward,
    send_request,
    get_default_socket_path,
)
from entangledpdf.socket_path import get_socket_path

# Import process tracking utilities from conftest
from tests.conftest import (
    kill_process_tree,
    track_test_process,
    untrack_test_process,
)

# Default test socket path (can be overridden via env var)
TEST_SOCKET_PATH = Path(os.getenv("ENTANGLEDPDF_TEST_SOCKET", "/tmp/entangledpdf_test.sock"))
TEST_SERVER_PORT = int(os.getenv("ENTANGLEDPDF_TEST_PORT", 18080))


@pytest.fixture(scope="module")
def test_certs(tmp_path_factory) -> Generator[tuple[Path, Path], None, None]:
    """Generate self-signed certificates for testing."""
    tmp_path = tmp_path_factory.mktemp("certs")
    cert_path = tmp_path / "test.crt"
    key_path = tmp_path / "test.key"
    
    # Generate certificate for localhost
    generate_self_signed_cert(
        hostname="localhost",
        cert_path=cert_path,
        key_path=key_path,
        days_valid=1  # Short-lived for tests
    )
    
    yield cert_path, key_path
    
    # Cleanup happens automatically when tmp_path is deleted


@pytest.fixture(scope="module")
def running_server(test_certs, tmp_path_factory, request):
    """Start a real entangle-pdf process for end-to-end testing.
    
    This fixture now includes robust cleanup:
    - Tracks process in temp file for zombie detection
    - Uses process tree kill (including children)
    - Handles both graceful and forceful termination
    - Cleans up even if tests are interrupted
    
    Yields:
        dict: Server info with 'port', 'socket_path', 'cert_path', 'key_path', 'process'
    """
    cert_path, key_path = test_certs
    port = TEST_SERVER_PORT
    socket_path = TEST_SOCKET_PATH
    
    # Remove socket if it exists from previous test run
    if socket_path.exists():
        try:
            socket_path.unlink()
        except OSError:
            pass
    
    # Create a temp directory for the server
    server_dir = tmp_path_factory.mktemp("server")
    static_dir = server_dir / "static"
    static_dir.mkdir()
    
    # Create minimal viewer.html
    viewer_html = static_dir / "viewer.html"
    viewer_html.write_text("""<!DOCTYPE html>
<html>
<head><title>Test PDF</title></head>
<body>
    <div id="viewer-container"></div>
    <script>
        window.PDF_CONFIG = { port: {{ port }}, filename: "{{ filename }}" };
    </script>
</body>
</html>""")
    
    # Build command to start server
    project_root = Path(__file__).parent.parent
    cmd = [
        sys.executable,
        str(project_root / "main.py"),
        "--port", str(port),
        "--ssl-cert", str(cert_path),
        "--ssl-key", str(key_path),
    ]
    
    # Set environment variables
    env = os.environ.copy()
    env["ENTANGLEDPDF_TESTING"] = "1"
    env["ENTANGLEDPDF_SOCKET"] = str(socket_path)  # Use custom socket for testing
    
    # Start server process
    process = subprocess.Popen(
        cmd,
        cwd=str(Path(__file__).parent.parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    
    # Track process for cleanup
    test_id = f"{request.node.name}_{time.time()}"
    track_test_process(process.pid, port, test_id)
    
    # Wait for server to be ready (check socket file exists)
    max_retries = 30
    server_ready = False
    for i in range(max_retries):
        if socket_path.exists():
            server_ready = True
            break
        time.sleep(0.5)
    
    if not server_ready:
        # Server didn't start - clean up and fail
        kill_process_tree(process.pid, timeout=2.0)
        untrack_test_process(process.pid)
        stdout, _ = process.communicate(timeout=5)
        raise RuntimeError(
            f"Server failed to start (socket not created).\n"
            f"output: {stdout.decode()}"
        )
    
    # Wait for server to be fully ready by checking /state endpoint via Unix socket
    http_ready = False
    for i in range(max_retries):
        try:
            result = send_request("GET", "/state", socket_path)
            if result.get("port") == port:
                http_ready = True
                break
        except Exception:
            time.sleep(0.5)
    
    if not http_ready:
        # Server didn't respond to HTTP requests
        kill_process_tree(process.pid, timeout=2.0)
        untrack_test_process(process.pid)
        stdout, _ = process.communicate(timeout=5)
        raise RuntimeError(
            f"Server started but not responding to HTTP requests.\n"
            f"output: {stdout.decode()}"
        )
    
    # Give server a bit more time to fully initialize
    time.sleep(0.5)
    
    server_info = {
        "port": port,
        "socket_path": socket_path,
        "cert_path": cert_path,
        "key_path": key_path,
        "process": process,
        "static_dir": static_dir,
        "_test_id": test_id,
    }
    
    yield server_info
    
    # Teardown: robust cleanup
    try:
        success = kill_process_tree(process.pid, timeout=5.0)
        if not success:
            print(f"Warning: Could not kill process {process.pid} gracefully", file=sys.stderr)
            try:
                os.kill(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
    except Exception as e:
        print(f"Warning: Error during server teardown: {e}", file=sys.stderr)
    finally:
        untrack_test_process(process.pid)
        # Clean up socket file
        if socket_path.exists():
            try:
                socket_path.unlink()
            except OSError:
                pass


@pytest.mark.slow
class TestSyncRemotePdfSubprocess:
    """End-to-end tests using real subprocesses for entangle-pdf sync."""

    def test_sync_remote_pdf_loads_pdf_successfully(self, running_server, tmp_path):
        """Real entangle-pdf sync call loads PDF into real server."""
        # Create a test PDF file
        pdf_file = tmp_path / "test_document.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        # Build command using new CLI structure (no --port or --api-key needed)
        cmd = [
            sys.executable,
            "-m", "entangledpdf.cli",
            "sync",
            "--socket-path", str(running_server["socket_path"]),
            str(pdf_file),
        ]
        
        # Run entangle-pdf sync
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        
        # Verify success
        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert "successfully" in result.stdout.lower() or "PDF loaded" in result.stdout
        
        # Verify server state via Unix socket API
        response = send_request(
            "GET",
            "/state",
            running_server["socket_path"],
        )
        
        assert response["pdf_loaded"] is True
        assert Path(response["pdf_file"]).name == pdf_file.name

    def test_sync_remote_pdf_with_synctex_forward(self, running_server, tmp_path):
        """Real entangle-pdf sync with synctex info performs search."""
        # Use the example PDF which has synctex data
        project_root = Path(__file__).parent.parent
        example_pdf = project_root / "examples" / "example.pdf"
        example_tex = project_root / "examples" / "example.tex"
        
        if not example_pdf.exists() or not example_tex.exists():
            pytest.skip("example.pdf or example.tex not found in examples/")
        
        # First load the PDF
        load_cmd = [
            sys.executable,
            "-m", "entangledpdf.cli",
            "sync",
            "--socket-path", str(running_server["socket_path"]),
            str(example_pdf),
        ]
        
        result = subprocess.run(
            load_cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        
        # Now run with synctex info as positional arg
        synctex_cmd = [
            sys.executable,
            "-m", "entangledpdf.cli",
            "sync",
            "--socket-path", str(running_server["socket_path"]),
            str(example_pdf),
            f"42:5:{example_tex}",
        ]
        
        result = subprocess.run(
            synctex_cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        
        # Verify command succeeded
        assert result.returncode == 0, f"Synctex forward failed: {result.stderr}"
        
        # Verify server state was updated (via webhook)
        response = send_request(
            "GET",
            "/state",
            running_server["socket_path"],
        )
        
        # Server should have updated state from webhook
        assert response["pdf_loaded"] is True

    def test_sync_remote_pdf_nonexistent_pdf_fails(self, running_server, tmp_path):
        """Nonexistent PDF file produces clear error."""
        nonexistent = tmp_path / "does_not_exist.pdf"
        
        cmd = [
            sys.executable,
            "-m", "entangledpdf.cli",
            "sync",
            "--socket-path", str(running_server["socket_path"]),
            str(nonexistent),
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        
        # Should fail
        assert result.returncode != 0
        # Error should mention file not found
        assert "not found" in result.stderr.lower() or "no such file" in result.stderr.lower()

    def test_sync_remote_pdf_verbose_output(self, running_server, tmp_path):
        """--verbose flag produces diagnostic output."""
        pdf_file = tmp_path / "test_verbose.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        cmd = [
            sys.executable,
            "-m", "entangledpdf.cli",
            "sync",
            "-v",
            "--socket-path", str(running_server["socket_path"]),
            str(pdf_file),
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        
        # Should succeed
        assert result.returncode == 0
        # Verbose output should include loading message
        assert "loading" in result.stdout.lower() or "pdf" in result.stdout.lower()

    def test_sync_remote_pdf_server_not_running(self, tmp_path):
        """Clear error when server is not running."""
        pdf_file = tmp_path / "test_noserver.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        # Use a socket path that definitely doesn't exist
        unused_socket = "/tmp/entangledpdf_unused_test.sock"
        
        cmd = [
            sys.executable,
            "-m", "entangledpdf.cli",
            "sync",
            "--socket-path", unused_socket,
            str(pdf_file),
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        
        # Should fail
        assert result.returncode != 0
        # Error should mention socket/connection issue
        error_lower = result.stderr.lower()
        assert any(x in error_lower for x in ["socket", "not running", "failed", "no such file"])

    def test_sync_remote_pdf_multiple_files_sequentially(self, running_server, tmp_path):
        """Can load multiple PDFs in sequence."""
        # Create two PDFs
        pdf1 = tmp_path / "document_one.pdf"
        pdf1.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        pdf2 = tmp_path / "document_two.pdf"
        pdf2.write_bytes(b"%PDF-1.4\n2 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        # Load first PDF
        cmd1 = [
            sys.executable,
            "-m", "entangledpdf.cli",
            "sync",
            "--socket-path", str(running_server["socket_path"]),
            str(pdf1),
        ]
        
        result1 = subprocess.run(
            cmd1,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result1.returncode == 0
        
        # Verify first PDF loaded
        state1 = send_request(
            "GET", "/state", running_server["socket_path"]
        )
        assert Path(state1["pdf_file"]).name == pdf1.name
        
        # Load second PDF
        cmd2 = [
            sys.executable,
            "-m", "entangledpdf.cli",
            "sync",
            "--socket-path", str(running_server["socket_path"]),
            str(pdf2),
        ]
        
        result2 = subprocess.run(
            cmd2,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result2.returncode == 0
        
        # Verify second PDF is now loaded
        state2 = send_request(
            "GET", "/state", running_server["socket_path"]
        )
        assert Path(state2["pdf_file"]).name == pdf2.name
        
        # Load first PDF again
        result3 = subprocess.run(
            cmd1,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result3.returncode == 0
        
        # Verify first PDF is loaded again
        state3 = send_request(
            "GET", "/state", running_server["socket_path"]
        )
        assert Path(state3["pdf_file"]).name == pdf1.name


@pytest.mark.slow
class TestLoadPdfClientFunction:
    """Integration tests using the load_pdf() function directly (not subprocess)."""

    def test_load_pdf_updates_server_state(self, running_server, tmp_path):
        """load_pdf() function updates server state via Unix socket."""
        pdf_file = tmp_path / "test_function.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        # Call load_pdf directly (uses Unix socket, no API key needed)
        result = load_pdf(
            pdf_file,
            socket_path=running_server["socket_path"],
        )
        
        assert result["status"] == "success"
        assert result["filename"] == pdf_file.name
        
        # Verify server state
        state = send_request(
            "GET", "/state", running_server["socket_path"]
        )
        assert state["pdf_file"] == str(pdf_file)

    def test_load_pdf_field_name_correct(self, running_server, tmp_path):
        """Verify load_pdf sends 'pdf_path' not 'pdf_file' to server."""
        pdf_file = tmp_path / "test_field.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        # This should succeed if field name is correct
        result = load_pdf(
            pdf_file,
            socket_path=running_server["socket_path"],
        )
        
        assert result["status"] == "success"
        assert "changed" in result
        assert result["changed"] is True


@pytest.mark.slow
class TestForwardSearchFunction:
    """Integration tests for forward_search() function."""

    def test_forward_search_triggers_webhook(self, running_server, tmp_path):
        """forward_search() calls webhook endpoint successfully."""
        # Use the example PDF which has synctex data
        project_root = Path(__file__).parent.parent
        example_pdf = project_root / "examples" / "example.pdf"
        example_tex = project_root / "examples" / "example.tex"
        
        if not example_pdf.exists() or not example_tex.exists():
            pytest.skip("example.pdf or example.tex not found in examples/")
        
        load_pdf(
            example_pdf,
            socket_path=running_server["socket_path"],
        )
        
        # Call forward_search (uses Unix socket, no API key needed)
        result = forward_search(
            line=42,
            column=5,
            tex_file=str(example_tex),
            pdf_file=str(example_pdf),
            socket_path=running_server["socket_path"],
        )
        
        # Should return success (webhook received)
        assert "status" in result
        assert result["status"] in ["success", "ok", "received"]


@pytest.mark.slow
class TestParseSynctexForwardInE2E:
    """E2E tests for parse_synctex_forward functionality."""

    def test_parse_and_use_synctex_in_subprocess(self, running_server, tmp_path):
        """Parse synctex argument and use in subprocess command."""
        # Use the example PDF which has synctex data
        project_root = Path(__file__).parent.parent
        example_pdf = project_root / "examples" / "example.pdf"
        example_tex = project_root / "examples" / "example.tex"
        
        if not example_pdf.exists() or not example_tex.exists():
            pytest.skip("example.pdf or example.tex not found in examples/")
        
        # Parse synctex argument
        line, col, tex = parse_synctex_forward(f"100:20:{example_tex}")
        assert line == 100
        assert col == 20
        assert tex == str(example_tex)
        
        # Load PDF first
        load_cmd = [
            sys.executable,
            "-m", "entangledpdf.cli",
            "sync",
            "--socket-path", str(running_server["socket_path"]),
            str(example_pdf),
        ]
        
        result = subprocess.run(
            load_cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        
        # Use parsed values in forward search
        synctex_arg = f"{line}:{col}:{tex}"
        
        forward_cmd = [
            sys.executable,
            "-m", "entangledpdf.cli",
            "sync",
            "--socket-path", str(running_server["socket_path"]),
            str(example_pdf),
            synctex_arg,
        ]
        
        result = subprocess.run(
            forward_cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        
        # Should succeed (even if synctex binary isn't available)
        assert result.returncode == 0
