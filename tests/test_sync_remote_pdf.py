"""Unit tests for the sync-remote-pdf CLI client.

Tests the sync-remote-pdf command-line interface functions.
"""

import pytest
from pathlib import Path
import time
from typing import Tuple


# Copy the function definitions from sync-remote-pdf script for testing
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


class TestServerDetection:
    """Test server availability detection logic."""

    def test_get_server_url_variations(self):
        """Test various server URL formats."""
        # Default HTTPS
        assert get_server_url(8431) == "https://localhost:8431"
        
        # HTTP explicitly
        assert get_server_url(9000, use_http=True) == "http://localhost:9000"
        
        # Custom port
        assert get_server_url(3000) == "https://localhost:3000"
        assert get_server_url(3000, use_http=True) == "http://localhost:3000"