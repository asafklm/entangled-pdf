"""End-to-end integration tests for pdf-server sync CLI with real server subprocess.

These tests spawn actual pdf-server and pdf-server sync processes to test real-world
usage without any mocking. Uses self-signed SSL certificates on port 18080.

Environment Variables:
    PDF_SERVER_TEST_PORT: Override default test port (default: 18080)
    PDF_SERVER_TEST_DIR: Override temp directory for test artifacts

Example:
    PDF_SERVER_TEST_PORT=28080 pytest tests/test_sync_e2e_subprocess.py -v
"""

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

from pdfserver.certs import generate_self_signed_cert
from pdfserver.sync import (
    create_ssl_context,
    forward_search,
    load_pdf,
    parse_synctex_forward,
    send_request,
)

# Default test port (can be overridden via env var)
TEST_SERVER_PORT = int(os.getenv("PDF_SERVER_TEST_PORT", 18080))
TEST_SERVER_HOST = "localhost"
TEST_API_KEY = "test-api-key-e2e-12345"


@pytest.fixture(scope="module")
def test_certs(tmp_path_factory) -> Generator[tuple[Path, Path], None, None]:
    """Generate self-signed certificates for testing."""
    tmp_path = tmp_path_factory.mktemp("certs")
    cert_path = tmp_path / "test.crt"
    key_path = tmp_path / "test.key"
    
    # Generate certificate for localhost
    generate_self_signed_cert(
        hostname=TEST_SERVER_HOST,
        cert_path=cert_path,
        key_path=key_path,
        days_valid=1  # Short-lived for tests
    )
    
    yield cert_path, key_path
    
    # Cleanup happens automatically when tmp_path is deleted


@pytest.fixture(scope="module")
def running_server(test_certs, tmp_path_factory):
    """Start a real pdf-server process for end-to-end testing.
    
    Yields:
        dict: Server info with 'port', 'api_key', 'cert_path', 'key_path', 'process'
    """
    cert_path, key_path = test_certs
    port = TEST_SERVER_PORT
    
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
    # Using python main.py directly
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
    env["PDF_SERVER_API_KEY"] = TEST_API_KEY
    env["PDF_SERVER_TESTING"] = "1"  # Flag to indicate test mode
    
    # Start server process
    process = subprocess.Popen(
        cmd,
        cwd=str(Path(__file__).parent.parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Merge stderr into stdout
    )
    
    # Wait for server to be ready (check with health endpoint or wait fixed time)
    max_retries = 30
    for i in range(max_retries):
        try:
            # Try to connect
            ctx = create_ssl_context()
            with socket.create_connection((TEST_SERVER_HOST, port), timeout=1):
                break
        except (socket.error, ConnectionRefusedError):
            time.sleep(0.5)
    else:
        # Server didn't start
        process.terminate()
        stdout, _ = process.communicate(timeout=5)
        raise RuntimeError(
            f"Server failed to start on port {port}.\n"
            f"output: {stdout.decode()}"
        )
    
    # Wait for server to be fully ready by checking /state endpoint
    import urllib.request
    for i in range(max_retries):
        try:
            url = f"https://{TEST_SERVER_HOST}:{port}/state"
            req = urllib.request.Request(url)
            ctx = create_ssl_context()
            with urllib.request.urlopen(req, context=ctx, timeout=2) as resp:
                if resp.status == 200:
                    break
        except Exception:
            time.sleep(0.5)
    else:
        # Server didn't respond to HTTP requests
        process.terminate()
        stdout, _ = process.communicate(timeout=5)
        raise RuntimeError(
            f"Server started but not responding to HTTP requests.\n"
            f"output: {stdout.decode()}"
        )
    
    # Give server a bit more time to fully initialize
    time.sleep(0.5)
    
    server_info = {
        "port": port,
        "api_key": TEST_API_KEY,
        "cert_path": cert_path,
        "key_path": key_path,
        "process": process,
        "static_dir": static_dir,
    }
    
    yield server_info
    
    # Teardown: terminate server
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


class TestSyncRemotePdfSubprocess:
    """End-to-end tests using real subprocesses for pdf-server sync."""

    def test_sync_remote_pdf_loads_pdf_successfully(self, running_server, tmp_path):
        """Real pdf-server sync call loads PDF into real server."""
        # Create a test PDF file
        pdf_file = tmp_path / "test_document.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        # Build command using new CLI structure
        cmd = [
            sys.executable,
            "-m", "pdfserver.cli",
            "sync",
            str(pdf_file),
            "--port", str(running_server["port"]),
            "--api-key", running_server["api_key"],
        ]
        
        # Run pdf-server sync
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        
        # Verify success
        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert "successfully" in result.stdout.lower() or "PDF loaded" in result.stdout
        
        # Verify server state via API
        response = send_request(
            "GET",
            "/state",
            running_server["port"],
            api_key=running_server["api_key"],
        )
        
        assert response["pdf_loaded"] is True
        assert response["filename"] == pdf_file.name

    def test_sync_remote_pdf_with_synctex_forward(self, running_server, tmp_path):
        """Real pdf-server sync with synctex info performs search."""
        # Create test PDF
        pdf_file = tmp_path / "test_synctex.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        # First load the PDF
        load_cmd = [
            sys.executable,
            "-m", "pdfserver.cli",
            "sync",
            str(pdf_file),
            "--port", str(running_server["port"]),
            "--api-key", running_server["api_key"],
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
            "-m", "pdfserver.cli",
            "sync",
            str(pdf_file),
            "42:5:chapter.tex",
            "--port", str(running_server["port"]),
            "--api-key", running_server["api_key"],
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
            running_server["port"],
            api_key=running_server["api_key"],
        )
        
        # Server should have updated state from webhook
        assert response["pdf_loaded"] is True
        # Note: Without actual synctex binary, the webhook may not update page/y
        # but the request should succeed

    def test_sync_remote_pdf_wrong_api_key_fails(self, running_server, tmp_path):
        """Wrong API key produces clear error message."""
        pdf_file = tmp_path / "test_auth.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        cmd = [
            sys.executable,
            "-m", "pdfserver.cli",
            "sync",
            str(pdf_file),
            "--port", str(running_server["port"]),
            "--api-key", "wrong-api-key",
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        
        # Should fail with non-zero exit code
        assert result.returncode != 0
        # Error message should mention authentication
        assert "authentication" in result.stderr.lower() or "auth" in result.stderr.lower() or "403" in result.stderr

    def test_sync_remote_pdf_nonexistent_pdf_fails(self, running_server, tmp_path):
        """Nonexistent PDF file produces clear error."""
        nonexistent = tmp_path / "does_not_exist.pdf"
        
        cmd = [
            sys.executable,
            "-m", "pdfserver.sync",
            str(nonexistent),
            "--port", str(running_server["port"]),
            "--api-key", running_server["api_key"],
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
            "-m", "pdfserver.sync",
            "-v",
            str(pdf_file),
            "--port", str(running_server["port"]),
            "--api-key", running_server["api_key"],
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
        
        # Use a port that's definitely not used (very high port)
        unused_port = 55555
        
        cmd = [
            sys.executable,
            "-m", "pdfserver.sync",
            str(pdf_file),
            "--port", str(unused_port),
            "--api-key", TEST_API_KEY,
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        
        # Should fail
        assert result.returncode != 0
        # Error should mention connection issue
        error_lower = result.stderr.lower()
        assert any(x in error_lower for x in ["connection", "refused", "failed", "request failed"])

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
            "-m", "pdfserver.sync",
            str(pdf1),
            "--port", str(running_server["port"]),
            "--api-key", running_server["api_key"],
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
            "GET", "/state", running_server["port"],
            api_key=running_server["api_key"]
        )
        assert state1["filename"] == pdf1.name
        
        # Load second PDF
        cmd2 = [
            sys.executable,
            "-m", "pdfserver.sync",
            str(pdf2),
            "--port", str(running_server["port"]),
            "--api-key", running_server["api_key"],
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
            "GET", "/state", running_server["port"],
            api_key=running_server["api_key"]
        )
        assert state2["filename"] == pdf2.name
        
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
            "GET", "/state", running_server["port"],
            api_key=running_server["api_key"]
        )
        assert state3["filename"] == pdf1.name

    def test_sync_remote_pdf_with_custom_port(self, running_server, tmp_path):
        """--port flag connects to correct server (redundant but explicit test)."""
        # This test verifies the custom port we set in running_server works
        pdf_file = tmp_path / "test_port.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        cmd = [
            sys.executable,
            "-m", "pdfserver.sync",
            str(pdf_file),
            "--port", str(running_server["port"]),
            "--api-key", running_server["api_key"],
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        
        assert result.returncode == 0
        
        # Verify via state endpoint
        state = send_request(
            "GET", "/state", running_server["port"],
            api_key=running_server["api_key"]
        )
        assert state["pdf_loaded"] is True


class TestLoadPdfClientFunction:
    """Integration tests using the load_pdf() function directly (not subprocess)."""

    def test_load_pdf_updates_server_state(self, running_server, tmp_path):
        """load_pdf() function updates server state via real HTTP."""
        pdf_file = tmp_path / "test_function.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        # Call load_pdf directly (it will make real HTTP request)
        result = load_pdf(
            pdf_file,
            port=running_server["port"],
            api_key=running_server["api_key"],
        )
        
        assert result["status"] == "success"
        assert result["filename"] == pdf_file.name
        
        # Verify server state
        state = send_request(
            "GET", "/state", running_server["port"],
            api_key=running_server["api_key"]
        )
        assert state["pdf_file"] == str(pdf_file)

    def test_load_pdf_field_name_correct(self, running_server, tmp_path):
        """Verify load_pdf sends 'pdf_path' not 'pdf_file' to server."""
        pdf_file = tmp_path / "test_field.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        # This should succeed if field name is correct
        result = load_pdf(
            pdf_file,
            port=running_server["port"],
            api_key=running_server["api_key"],
        )
        
        assert result["status"] == "success"
        assert "changed" in result
        assert result["changed"] is True


class TestForwardSearchFunction:
    """Integration tests for forward_search() function."""

    def test_forward_search_triggers_webhook(self, running_server, tmp_path):
        """forward_search() calls webhook endpoint successfully."""
        # First load a PDF
        pdf_file = tmp_path / "test_forward.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        load_pdf(
            pdf_file,
            port=running_server["port"],
            api_key=running_server["api_key"],
        )
        
        # Call forward_search
        result = forward_search(
            line=42,
            column=5,
            tex_file="chapter.tex",
            port=running_server["port"],
            api_key=running_server["api_key"],
        )
        
        # Should return success (webhook received)
        assert "status" in result
        assert result["status"] in ["success", "ok", "received"]


class TestPortOverride:
    """Test port conflict workaround via environment variable."""

    def test_port_override_via_env_var(self, tmp_path, monkeypatch):
        """PDF_SERVER_TEST_PORT env var overrides default port."""
        # This test just verifies the env var is respected in the fixture
        # The actual port override would require restarting the server fixture
        # So we just verify the constant is set correctly
        custom_port = 28080
        monkeypatch.setenv("PDF_SERVER_TEST_PORT", str(custom_port))
        
        # Re-import to pick up new value
        # Note: In real usage, user would run pytest with the env var
        import importlib
        import tests.test_sync_e2e_subprocess as test_module
        importlib.reload(test_module)
        
        assert test_module.TEST_SERVER_PORT == custom_port


class TestParseSynctexForwardInE2E:
    """E2E tests for parse_synctex_forward functionality."""

    def test_parse_and_use_synctex_in_subprocess(self, running_server, tmp_path):
        """Parse synctex argument and use in subprocess command."""
        pdf_file = tmp_path / "test_synctex_e2e.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
        
        # Parse synctex argument
        line, col, tex = parse_synctex_forward("100:20:section.tex")
        assert line == 100
        assert col == 20
        assert tex == "section.tex"
        
        # Load PDF first
        load_cmd = [
            sys.executable,
            "-m", "pdfserver.sync",
            str(pdf_file),
            "--port", str(running_server["port"]),
            "--api-key", running_server["api_key"],
        ]
        
        result = subprocess.run(
            load_cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        
        # Use parsed values in forward search
        # Note: pdf-server sync takes synctex info as positional arg
        synctex_arg = f"{line}:{col}:{tex}"
        
        forward_cmd = [
            sys.executable,
            "-m", "pdfserver.cli",
            "sync",
            str(pdf_file),
            synctex_arg,
            "--port", str(running_server["port"]),
            "--api-key", running_server["api_key"],
        ]
        
        result = subprocess.run(
            forward_cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        
        # Should succeed (even if synctex binary isn't available)
        # The webhook will be called
        assert result.returncode == 0
