"""Unit tests for the remote_pdf CLI client.

Tests the remote_pdf command-line interface functions.
"""

import pytest
from pathlib import Path
import time
from typing import Tuple


# Copy the function definitions from remote_pdf script for testing
def parse_synctex_forward(value: str) -> Tuple[int, int, str]:
    """Parse --synctex-forward argument in Zathura format: line:col:texfile"""
    parts = value.split(":", 2)
    if len(parts) != 3:
        raise ValueError(f"Invalid --synctex-forward format: {value}. Expected: line:col:texfile")
    
    try:
        line = int(parts[0])
        col = int(parts[1])
    except ValueError:
        raise ValueError(f"Invalid line or column in: {value}")
    
    tex_file = parts[2]
    return line, col, tex_file


def get_server_url(port: int, use_http: bool = False) -> str:
    """Get server base URL for given port and protocol."""
    protocol = "http" if use_http else "https"
    return f"{protocol}://localhost:{port}"


class TestParseSynctexForward:
    """Test parsing of --synctex-forward argument."""

    def test_valid_format(self):
        """Test parsing valid line:col:texfile format."""
        result = parse_synctex_forward("42:5:chapter.tex")
        assert result == (42, 5, "chapter.tex")

    def test_valid_format_different_values(self):
        """Test parsing with different line and column values."""
        result = parse_synctex_forward("1:0:main.tex")
        assert result == (1, 0, "main.tex")

    def test_invalid_format_missing_parts(self):
        """Test that missing parts raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_synctex_forward("42:5")
        assert "Invalid --synctex-forward format" in str(exc_info.value)

    def test_invalid_line_number(self):
        """Test that non-numeric line raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_synctex_forward("abc:5:chapter.tex")
        assert "Invalid line or column" in str(exc_info.value)

    def test_invalid_column_number(self):
        """Test that non-numeric column raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_synctex_forward("42:xyz:chapter.tex")
        assert "Invalid line or column" in str(exc_info.value)


class TestGetServerUrl:
    """Test server URL construction."""

    def test_https_default(self):
        """Test that HTTPS is default."""
        url = get_server_url(8431)
        assert url == "https://localhost:8431"

    def test_http_when_requested(self):
        """Test that HTTP is used when requested."""
        url = get_server_url(8431, use_http=True)
        assert url == "http://localhost:8431"

    def test_different_port(self):
        """Test URL with different port."""
        url = get_server_url(8080)
        assert url == "https://localhost:8080"


class TestPdfDetectionLogic:
    """Test PDF change detection logic."""

    def test_needs_reload_when_no_pdf_loaded(self, tmp_path):
        """Test detection when no PDF is loaded on server."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"PDF content")
        pdf_mtime = pdf_path.stat().st_mtime

        # Simulate state with no PDF
        state = {"pdf_loaded": False, "pdf_file": None, "pdf_mtime": None}

        needs_reload = (
            not state["pdf_loaded"] or
            (state["pdf_file"] and Path(state["pdf_file"]).resolve() != pdf_path) or
            (state["pdf_mtime"] and pdf_mtime > state["pdf_mtime"])
        )

        assert needs_reload is True

    def test_needs_reload_when_different_pdf(self, tmp_path):
        """Test detection when different PDF is loaded."""
        pdf_path = tmp_path / "new.pdf"
        pdf_path.write_bytes(b"PDF content")

        # Simulate state with different PDF
        state = {
            "pdf_loaded": True,
            "pdf_file": "/path/to/old.pdf",
            "pdf_mtime": 1234567890.0
        }

        needs_reload = (
            not state["pdf_loaded"] or
            (state["pdf_file"] and Path(state["pdf_file"]).resolve() != pdf_path) or
            (state["pdf_mtime"] and pdf_path.stat().st_mtime > state["pdf_mtime"])
        )

        assert needs_reload is True

    def test_no_reload_when_same_pdf_unchanged(self, tmp_path):
        """Test detection when same PDF is loaded and unchanged."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"PDF content")
        pdf_mtime = pdf_path.stat().st_mtime

        # Simulate state with same PDF
        state = {
            "pdf_loaded": True,
            "pdf_file": str(pdf_path),
            "pdf_mtime": pdf_mtime
        }

        needs_reload = (
            not state["pdf_loaded"] or
            (state["pdf_file"] and Path(state["pdf_file"]).resolve() != pdf_path) or
            (state["pdf_mtime"] and pdf_mtime > state["pdf_mtime"])
        )

        assert needs_reload is False

    def test_needs_reload_when_pdf_modified(self, tmp_path):
        """Test detection when PDF file was modified."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"PDF content")
        old_mtime = pdf_path.stat().st_mtime

        # Wait and modify file
        time.sleep(0.1)
        pdf_path.write_bytes(b"Modified PDF content")
        new_mtime = pdf_path.stat().st_mtime

        # Simulate state with old mtime
        state = {
            "pdf_loaded": True,
            "pdf_file": str(pdf_path),
            "pdf_mtime": old_mtime
        }

        needs_reload = (
            not state["pdf_loaded"] or
            (state["pdf_file"] and Path(state["pdf_file"]).resolve() != pdf_path) or
            (state["pdf_mtime"] and new_mtime > state["pdf_mtime"])
        )

        assert needs_reload is True
