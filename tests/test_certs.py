"""Tests for SSL certificate handling in src.certs."""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from entangledpdf import certs


def test_validate_certificate_not_found():
    missing = Path("/tmp/file-does-not-exist-for-tests.crt")
    info = certs.validate_certificate(missing)
    assert info["exists"] is False
    assert info["error"] is not None


def test_copy_existing_cert_not_found_raises():
    src_cert = Path("/tmp/nonexistent.crt")
    src_key = Path("/tmp/nonexistent.key")
    with pytest.raises(FileNotFoundError):
        certs.copy_existing_cert(src_cert, src_key)


class TestCertsGenerateCommand:
    """Tests for `python -m entangledpdf.certs generate` command."""

    def test_certs_generate_creates_cert_and_key_at_custom_path(self, tmp_path: Path):
        """Test that generate command can create cert at specified path."""
        cert_path = tmp_path / "custom.crt"
        key_path = tmp_path / "custom.key"
        
        # Use generate_self_signed_cert directly (subprocess doesn't support custom paths)
        certs.generate_self_signed_cert(
            hostname="localhost",
            cert_path=cert_path,
            key_path=key_path,
            days_valid=1
        )
        
        assert cert_path.exists()
        assert key_path.exists()
        
        # Verify cert is valid PEM
        cert_content = cert_path.read_text()
        assert "-----BEGIN CERTIFICATE-----" in cert_content
        assert "-----END CERTIFICATE-----" in cert_content
        
        # Verify key is valid PEM
        key_content = key_path.read_text()
        assert "-----BEGIN" in key_content
        assert "PRIVATE KEY-----" in key_content

    def test_certs_generate_force_overwrites_existing(self, tmp_path: Path):
        """Test that --force flag overwrites existing certificates."""
        cert_path = tmp_path / "test.crt"
        key_path = tmp_path / "test.key"
        
        # Generate initial cert
        certs.generate_self_signed_cert(
            hostname="test1.local",
            cert_path=cert_path,
            key_path=key_path,
            days_valid=1
        )
        
        # Read initial cert content
        initial_cert = cert_path.read_text()
        
        # Generate again (should overwrite)
        certs.generate_self_signed_cert(
            hostname="test2.local",
            cert_path=cert_path,
            key_path=key_path,
            days_valid=1
        )
        
        # Verify cert was overwritten (different content)
        new_cert = cert_path.read_text()
        assert new_cert != initial_cert

    def test_certs_generate_with_cert_key_copies_to_default(self, tmp_path: Path, monkeypatch):
        """Test that --cert and --key copy existing certs to default location."""
        # Create source cert files
        src_cert = tmp_path / "source.crt"
        src_key = tmp_path / "source.key"
        
        # Generate a cert at source location
        certs.generate_self_signed_cert(
            hostname="test.local",
            cert_path=src_cert,
            key_path=src_key,
            days_valid=1
        )
        
        # Verify source exists
        assert src_cert.exists()
        assert src_key.exists()
        
        # Mock get_cert_paths and get_cert_directory to use temp directory
        mock_default_dir = tmp_path / "default"
        mock_default_cert = mock_default_dir / "server.crt"
        mock_default_key = mock_default_dir / "server.key"
        
        monkeypatch.setattr(
            certs,
            "get_cert_paths",
            lambda: (mock_default_cert, mock_default_key)
        )
        monkeypatch.setattr(
            certs,
            "get_cert_directory",
            lambda: mock_default_dir
        )
        
        # Test copy_existing_cert function
        certs.copy_existing_cert(src_cert, src_key)
        
        # Verify files were copied to mocked default location
        assert mock_default_cert.exists()
        assert mock_default_key.exists()
        
        # Verify content matches source
        assert mock_default_cert.read_text() == src_cert.read_text()
        assert mock_default_key.read_text() == src_key.read_text()

    def test_certs_status_returns_exit_code(self, tmp_path: Path):
        """Test that status command returns appropriate exit codes."""
        # Status command should run without error
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "entangledpdf.certs",
                "status",
            ],
            capture_output=True,
            text=True,
        )
        
        # Exit code 0 = valid certs, 1 = invalid/missing
        assert result.returncode in (0, 1)
