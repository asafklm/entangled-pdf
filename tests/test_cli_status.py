"""Tests for 'entangle-pdf status' command.

Tests server status checking including:
- Server not running detection
- Server running detection
- PDF loaded status display
- Authentication token display
- Custom port handling
- HTTP vs HTTPS detection
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests
import urllib3

from entangledpdf.certs import generate_self_signed_cert

# Import process tracking utilities
from tests.conftest import (
    kill_process_tree,
    track_test_process,
    untrack_test_process,
)
from tests.test_cli_integration import get_cli_path
from tests.test_cli_start import get_test_port, wait_for_server

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@pytest.fixture
def test_certs(tmp_path):
    """Generate self-signed certificates for testing."""
    cert_path = tmp_path / "test.crt"
    key_path = tmp_path / "test.key"
    
    generate_self_signed_cert(
        hostname="localhost",
        cert_path=cert_path,
        key_path=key_path,
        days_valid=1
    )
    
    return cert_path, key_path


class TestStatusServerNotRunning:
    """Test suite for when server is not running."""
    
    def test_status_server_not_running(self):
        """Shows 'Server not running' when no server."""
        port = get_test_port()
        
        # Ensure no server on this port
        env = os.environ.copy()
        env["ENTANGLEDPDF_API_KEY"] = "test-status-key"
        
        result = subprocess.run(
            [str(get_cli_path()), "status", "--port", str(port)],
            capture_output=True,
            text=True,
            env=env,
        )
        
        # Should succeed (exit code 0)
        assert result.returncode == 0, \
            f"status should succeed even when server not running: {result.stderr}"
        
        # Output should indicate server not running
        output = result.stdout.lower()
        assert "not running" in output or \
               "no server" in output or \
               "server" in output, \
            f"Should indicate server not running, got: {result.stdout}"
    
    def test_status_different_port_not_running(self):
        """Checks correct port when server not running."""
        port1 = get_test_port()
        port2 = get_test_port()
        
        env = os.environ.copy()
        env["ENTANGLEDPDF_API_KEY"] = "test-status-key"
        
        # Check port1
        result1 = subprocess.run(
            [str(get_cli_path()), "status", "--port", str(port1)],
            capture_output=True,
            text=True,
            env=env,
        )
        
        assert "not running" in result1.stdout.lower() or \
               result1.returncode == 0, \
            f"Port {port1} should show not running: {result1.stdout}"
        
        # Check port2
        result2 = subprocess.run(
            [str(get_cli_path()), "status", "--port", str(port2)],
            capture_output=True,
            text=True,
            env=env,
        )
        
        assert "not running" in result2.stdout.lower() or \
               result2.returncode == 0, \
            f"Port {port2} should show not running: {result2.stdout}"


class TestStatusServerRunning:
    """Test suite for when server is running."""
    
    def test_status_server_running_no_pdf(self, test_certs):
        """Shows server status when running but no PDF loaded."""
        port = get_test_port()
        cert_path, key_path = test_certs
        
        env = os.environ.copy()
        env["ENTANGLEDPDF_API_KEY"] = "test-status-key-no-pdf"
        
        # Start server
        cmd = [
            str(get_cli_path()),
            "start",
            "--port", str(port),
            "--ssl-cert", str(cert_path),
            "--ssl-key", str(key_path),
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        
        track_test_process(process.pid, port, "test_status_no_pdf")
        
        try:
            # Wait for server
            assert wait_for_server(port, "https", timeout=10.0), \
                "Server failed to start"
            
            # Run status
            result = subprocess.run(
                [str(get_cli_path()), "status", "--port", str(port)],
                capture_output=True,
                text=True,
                env=env,
            )
            
            assert result.returncode == 0, \
                f"status failed: {result.stderr}"
            
            output = result.stdout.lower()
            
            # Should show server running
            assert "running" in output, \
                f"Should show 'running', got: {result.stdout}"
            
            # Should show port
            assert str(port) in result.stdout, \
                f"Should show port {port}, got: {result.stdout}"
            
            # Should indicate no PDF (waiting or none)
            assert "waiting" in output or "none" in output or "no pdf" in output, \
                f"Should indicate no PDF loaded, got: {result.stdout}"
            
        finally:
            kill_process_tree(process.pid, timeout=3.0)
            untrack_test_process(process.pid)
            process.wait(timeout=5)
    
    def test_status_server_running_with_pdf(self, test_certs, tmp_path):
        """Shows PDF file path when PDF loaded."""
        port = get_test_port()
        cert_path, key_path = test_certs
        
        env = os.environ.copy()
        env["ENTANGLEDPDF_API_KEY"] = "test-status-key-with-pdf"
        
        # Create a test PDF
        test_pdf = tmp_path / "test_document.pdf"
        test_pdf.write_bytes(b"%PDF-1.4 test content for status")
        
        # Start server
        cmd = [
            str(get_cli_path()),
            "start",
            "--port", str(port),
            "--ssl-cert", str(cert_path),
            "--ssl-key", str(key_path),
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        
        track_test_process(process.pid, port, "test_status_with_pdf")
        
        try:
            # Wait for server
            assert wait_for_server(port, "https", timeout=10.0), \
                "Server failed to start"
            
            # Load PDF via API
            headers = {"X-API-Key": "test-status-key-with-pdf"}
            load_resp = requests.post(
                f"https://localhost:{port}/api/load-pdf",
                json={"pdf_path": str(test_pdf)},
                headers=headers,
                timeout=2,
                verify=False
            )
            
            assert load_resp.status_code == 200, \
                f"Failed to load PDF: {load_resp.text}"
            
            # Run status
            result = subprocess.run(
                [str(get_cli_path()), "status", "--port", str(port)],
                capture_output=True,
                text=True,
                env=env,
            )
            
            assert result.returncode == 0, \
                f"status failed: {result.stderr}"
            
            output = result.stdout
            
            # Should show server running
            assert "running" in output.lower(), \
                f"Should show 'running', got: {output}"
            
            # Should show PDF file path (or name)
            assert "test_document.pdf" in output or "pdf" in output.lower(), \
                f"Should show PDF info, got: {output}"
            
        finally:
            kill_process_tree(process.pid, timeout=3.0)
            untrack_test_process(process.pid)
            process.wait(timeout=5)
    
    def test_status_shows_authentication_token(self, test_certs):
        """Shows WebSocket token when inverse search enabled."""
        port = get_test_port()
        cert_path, key_path = test_certs
        
        env = os.environ.copy()
        env["ENTANGLEDPDF_API_KEY"] = "test-status-key-token"
        
        # Create a test PDF
        test_pdf = cert_path.parent / "test_with_token.pdf"
        test_pdf.write_bytes(b"%PDF-1.4 test")
        
        # Start server with inverse search
        cmd = [
            str(get_cli_path()),
            "start",
            "--port", str(port),
            "--ssl-cert", str(cert_path),
            "--ssl-key", str(key_path),
            "--inverse-search-nvim",
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        
        track_test_process(process.pid, port, "test_status_token")
        
        try:
            # Wait for server
            assert wait_for_server(port, "https", timeout=10.0), \
                "Server failed to start"
            
            # Load PDF to trigger token generation
            headers = {"X-API-Key": "test-status-key-token"}
            load_resp = requests.post(
                f"https://localhost:{port}/api/load-pdf",
                json={
                    "pdf_path": str(test_pdf),
                    "inverse_search_command": "nvr --remote-silent +%{line} %{file}"
                },
                headers=headers,
                timeout=2,
                verify=False
            )
            
            # Run status
            result = subprocess.run(
                [str(get_cli_path()), "status", "--port", str(port)],
                capture_output=True,
                text=True,
                env=env,
            )
            
            assert result.returncode == 0
            output = result.stdout
            
            # Should show authentication token
            assert "token" in output.lower() or "authentication" in output.lower(), \
                f"Should show authentication token, got: {output}"
            
        finally:
            kill_process_tree(process.pid, timeout=3.0)
            untrack_test_process(process.pid)
            process.wait(timeout=5)


class TestStatusCustomPort:
    """Test suite for custom port handling."""
    
    def test_status_custom_port(self, test_certs):
        """--port flag checks correct port."""
        port1 = get_test_port()
        port2 = get_test_port()
        cert_path, key_path = test_certs
        
        env = os.environ.copy()
        env["ENTANGLEDPDF_API_KEY"] = "test-status-key-port"
        
        # Start server on port1
        cmd = [
            str(get_cli_path()),
            "start",
            "--port", str(port1),
            "--ssl-cert", str(cert_path),
            "--ssl-key", str(key_path),
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        
        track_test_process(process.pid, port1, "test_status_port")
        
        try:
            # Wait for server
            assert wait_for_server(port1, "https", timeout=10.0), \
                "Server failed to start"
            
            # Check port1 - should show running
            result1 = subprocess.run(
                [str(get_cli_path()), "status", "--port", str(port1)],
                capture_output=True,
                text=True,
                env=env,
            )
            
            assert "running" in result1.stdout.lower(), \
                f"Port {port1} should show running: {result1.stdout}"
            
            # Check port2 - should show not running
            result2 = subprocess.run(
                [str(get_cli_path()), "status", "--port", str(port2)],
                capture_output=True,
                text=True,
                env=env,
            )
            
            assert "not running" in result2.stdout.lower() or \
                   "no server" in result2.stdout.lower(), \
                f"Port {port2} should show not running: {result2.stdout}"
            
        finally:
            kill_process_tree(process.pid, timeout=3.0)
            untrack_test_process(process.pid)
            process.wait(timeout=5)
    
    def test_status_env_port_override(self, test_certs):
        """ENTANGLEDPDF_PORT env var works with status."""
        port = get_test_port()
        cert_path, key_path = test_certs
        
        env = os.environ.copy()
        env["ENTANGLEDPDF_API_KEY"] = "test-status-key-env"
        env["ENTANGLEDPDF_PORT"] = str(port)
        
        # Start server (will use env var for port)
        cmd = [
            str(get_cli_path()),
            "start",
            "--ssl-cert", str(cert_path),
            "--ssl-key", str(key_path),
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        
        track_test_process(process.pid, port, "test_status_env_port")
        
        try:
            # Wait for server
            assert wait_for_server(port, "https", timeout=10.0), \
                "Server failed to start"
            
            # Run status without --port (should use env var)
            result = subprocess.run(
                [str(get_cli_path()), "status"],  # No --port
                capture_output=True,
                text=True,
                env=env,
            )
            
            assert "running" in result.stdout.lower(), \
                f"Status should detect server on port {port} from env: {result.stdout}"
            
        finally:
            kill_process_tree(process.pid, timeout=3.0)
            untrack_test_process(process.pid)
            process.wait(timeout=5)


class TestStatusHttpHttps:
    """Test suite for HTTP vs HTTPS detection."""
    
    def test_status_http_mode(self):
        """Shows http:// URL when server in HTTP mode."""
        port = get_test_port()
        
        env = os.environ.copy()
        env["ENTANGLEDPDF_API_KEY"] = "test-status-key-http"
        
        # Start server in HTTP mode
        cmd = [
            str(get_cli_path()),
            "start",
            "--port", str(port),
            "--http",
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        
        track_test_process(process.pid, port, "test_status_http")
        
        try:
            # Wait for server
            assert wait_for_server(port, "http", timeout=10.0), \
                "HTTP server failed to start"
            
            # Run status
            result = subprocess.run(
                [str(get_cli_path()), "status", "--port", str(port)],
                capture_output=True,
                text=True,
                env=env,
            )
            
            assert result.returncode == 0
            
            # URL should show http:// not https://
            assert f"http://localhost:{port}" in result.stdout, \
                f"Should show http:// URL, got: {result.stdout}"
            
        finally:
            kill_process_tree(process.pid, timeout=3.0)
            untrack_test_process(process.pid)
            process.wait(timeout=5)
    
    def test_status_https_mode(self, test_certs):
        """Shows https:// URL when server in HTTPS mode."""
        port = get_test_port()
        cert_path, key_path = test_certs
        
        env = os.environ.copy()
        env["ENTANGLEDPDF_API_KEY"] = "test-status-key-https"
        
        # Start server in HTTPS mode
        cmd = [
            str(get_cli_path()),
            "start",
            "--port", str(port),
            "--ssl-cert", str(cert_path),
            "--ssl-key", str(key_path),
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        
        track_test_process(process.pid, port, "test_status_https")
        
        try:
            # Wait for server
            assert wait_for_server(port, "https", timeout=10.0), \
                "HTTPS server failed to start"
            
            # Run status
            result = subprocess.run(
                [str(get_cli_path()), "status", "--port", str(port)],
                capture_output=True,
                text=True,
                env=env,
            )
            
            assert result.returncode == 0
            
            # URL should show https://
            assert f"https://localhost:{port}" in result.stdout, \
                f"Should show https:// URL, got: {result.stdout}"
            
        finally:
            kill_process_tree(process.pid, timeout=3.0)
            untrack_test_process(process.pid)
            process.wait(timeout=5)