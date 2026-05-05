"""Tests for Unix socket path management.

Tests the socket_path module functions for path resolution,
directory creation, and stale socket detection.
"""

import os
import socket
from pathlib import Path
from unittest.mock import patch

import pytest

from entangledpdf.socket_path import (
    ensure_socket_directory,
    get_socket_path,
    is_server_running,
    prepare_socket_path,
    remove_stale_socket,
)


class TestGetSocketPath:
    """Test socket path resolution."""

    def test_env_variable_takes_precedence(self, tmp_path):
        """Test that ENTANGLEDPDF_SOCKET env var is used first."""
        custom_path = str(tmp_path / "custom.sock")
        with patch.dict(os.environ, {"ENTANGLEDPDF_SOCKET": custom_path}):
            result = get_socket_path()
            assert str(result) == custom_path

    def test_xdg_runtime_dir_used_when_available(self, tmp_path):
        """Test XDG_RUNTIME_DIR fallback."""
        with patch.dict(os.environ, {
            "ENTANGLEDPDF_SOCKET": "",  # Not set
            "XDG_RUNTIME_DIR": str(tmp_path),
        }):
            result = get_socket_path()
            expected = tmp_path / "entangledpdf" / "server.sock"
            assert result == expected

    def test_home_fallback(self, tmp_path):
        """Test home directory fallback."""
        with patch.dict(os.environ, {
            "ENTANGLEDPDF_SOCKET": "",
            "XDG_RUNTIME_DIR": "",
        }):
            with patch.object(Path, 'home', return_value=tmp_path):
                result = get_socket_path()
                expected = tmp_path / ".local" / "run" / "entangledpdf" / "server.sock"
                assert result == expected

    def test_returns_absolute_path(self):
        """Test that returned path is always absolute."""
        result = get_socket_path()
        assert result.is_absolute()

    def test_ends_with_server_sock(self):
        """Test that path ends with server.sock."""
        result = get_socket_path()
        assert result.name == "server.sock"


class TestEnsureSocketDirectory:
    """Test directory creation with permissions."""

    def test_creates_directory_if_not_exists(self, tmp_path):
        """Test directory is created when it doesn't exist."""
        socket_path = tmp_path / "subdir" / "test.sock"
        assert not socket_path.parent.exists()
        
        ensure_socket_directory(socket_path)
        
        assert socket_path.parent.exists()

    def test_directory_has_correct_permissions(self, tmp_path):
        """Test directory is created with 0700 permissions."""
        socket_path = tmp_path / "subdir" / "test.sock"
        
        ensure_socket_directory(socket_path)
        
        stat = socket_path.parent.stat()
        # Check owner has read/write/execute (0o700)
        assert stat.st_mode & 0o700 == 0o700

    def test_no_error_if_directory_exists(self, tmp_path):
        """Test no error if directory already exists."""
        socket_path = tmp_path / "existing" / "test.sock"
        socket_path.parent.mkdir(parents=True)
        
        # Should not raise
        ensure_socket_directory(socket_path)
        
        assert socket_path.parent.exists()


class TestIsServerRunning:
    """Test server detection via socket connection."""

    def test_returns_false_if_socket_not_exists(self, tmp_path):
        """Test returns False when socket file doesn't exist."""
        socket_path = tmp_path / "nonexistent.sock"
        
        result = is_server_running(socket_path)
        
        assert result is False

    def test_returns_false_if_connection_refused(self, tmp_path):
        """Test returns False when socket exists but no server listening."""
        socket_path = tmp_path / "stale.sock"
        # Create a socket file without a listening server
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(str(socket_path))
            sock.close()
            
            result = is_server_running(socket_path)
            assert result is False
        finally:
            if socket_path.exists():
                socket_path.unlink()

    def test_returns_true_if_server_listening(self, tmp_path):
        """Test returns True when server is listening on socket."""
        socket_path = tmp_path / "live.sock"
        
        # Create a server socket
        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server_sock.bind(str(socket_path))
            server_sock.listen(1)
            
            result = is_server_running(socket_path)
            assert result is True
        finally:
            server_sock.close()
            if socket_path.exists():
                socket_path.unlink()


class TestRemoveStaleSocket:
    """Test stale socket cleanup."""

    def test_returns_false_if_socket_not_exists(self, tmp_path):
        """Test returns False when no socket file."""
        socket_path = tmp_path / "nonexistent.sock"
        
        result = remove_stale_socket(socket_path)
        
        assert result is False

    def test_returns_false_if_server_running(self, tmp_path):
        """Test returns False when server is actually running."""
        socket_path = tmp_path / "live.sock"
        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server_sock.bind(str(socket_path))
            server_sock.listen(1)
            
            result = remove_stale_socket(socket_path)
            assert result is False
            assert socket_path.exists()  # Should not be removed
        finally:
            server_sock.close()
            if socket_path.exists():
                socket_path.unlink()

    def test_returns_true_and_removes_stale_socket(self, tmp_path):
        """Test returns True and removes stale socket."""
        socket_path = tmp_path / "stale.sock"
        # Create socket without listening server
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(str(socket_path))
            sock.close()
            
            result = remove_stale_socket(socket_path)
            assert result is True
            assert not socket_path.exists()
        finally:
            if socket_path.exists():
                socket_path.unlink()


class TestPrepareSocketPath:
    """Test socket path preparation for server startup."""

    def test_creates_directory(self, tmp_path):
        """Test that directory is created."""
        socket_path = tmp_path / "newdir" / "test.sock"
        
        prepare_socket_path(socket_path)
        
        assert socket_path.parent.exists()

    def test_removes_stale_socket(self, tmp_path):
        """Test that stale socket is removed."""
        socket_path = tmp_path / "stale.sock"
        # Create stale socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(str(socket_path))
            sock.close()
            
            prepare_socket_path(socket_path)
            
            assert not socket_path.exists()
        finally:
            if socket_path.exists():
                socket_path.unlink()

    def test_raises_if_server_running(self, tmp_path):
        """Test that RuntimeError is raised if server already running."""
        socket_path = tmp_path / "live.sock"
        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server_sock.bind(str(socket_path))
            server_sock.listen(1)
            
            with pytest.raises(RuntimeError) as exc_info:
                prepare_socket_path(socket_path)
            
            assert "already running" in str(exc_info.value).lower()
        finally:
            server_sock.close()
            if socket_path.exists():
                socket_path.unlink()

    def test_succeeds_if_clean_state(self, tmp_path):
        """Test that preparation succeeds in clean state."""
        socket_path = tmp_path / "clean" / "test.sock"
        
        # Should not raise
        prepare_socket_path(socket_path)
        
        assert socket_path.parent.exists()
        assert not socket_path.exists()  # Socket not created yet


class TestIntegration:
    """Integration tests for socket path workflow."""

    def test_full_workflow_clean_startup(self, tmp_path):
        """Test complete workflow: prepare -> no server running -> ready."""
        socket_path = tmp_path / "workflow" / "test.sock"
        
        # Prepare
        prepare_socket_path(socket_path)
        
        # Verify not running
        assert not is_server_running(socket_path)
        
        # Directory exists
        assert socket_path.parent.exists()

    def test_full_workflow_stale_cleanup(self, tmp_path):
        """Test complete workflow: stale socket -> cleanup -> ready."""
        socket_path = tmp_path / "workflow" / "test.sock"
        
        # Create parent directory first
        socket_path.parent.mkdir(parents=True)
        
        # Create stale socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(str(socket_path))
            sock.close()
            
            # Prepare should clean it up
            prepare_socket_path(socket_path)
            
            # Verify cleaned
            assert not socket_path.exists()
            assert not is_server_running(socket_path)
        finally:
            if socket_path.exists():
                socket_path.unlink()

    def test_full_workflow_running_detection(self, tmp_path):
        """Test complete workflow: server running -> error."""
        socket_path = tmp_path / "workflow" / "test.sock"
        
        # Create parent directory first
        socket_path.parent.mkdir(parents=True)
        
        # Start actual server
        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server_sock.bind(str(socket_path))
            server_sock.listen(1)
            
            # Prepare should fail
            with pytest.raises(RuntimeError):
                prepare_socket_path(socket_path)
        finally:
            server_sock.close()
            if socket_path.exists():
                socket_path.unlink()
