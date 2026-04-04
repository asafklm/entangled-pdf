"""Unit tests for pdf-server sync client utility functions.

Tests the utility functions from entangledpdf/sync that support the 
CLI client functionality (argument parsing, URL construction, etc.).
"""

import pytest
from pathlib import Path

from entangledpdf.sync import parse_synctex_forward, get_server_url


class TestParseSynctexForward:
    """Test parsing of --synctex-forward argument."""

    def test_valid_format(self):
        """Test parsing valid line:column:file format."""
        result = parse_synctex_forward("42:5:chapter.tex")
        assert result == (42, 5, "chapter.tex")

    def test_valid_format_different_values(self):
        """Test parsing with different line and column values."""
        result = parse_synctex_forward("1:0:main.tex")
        assert result == (1, 0, "main.tex")

    def test_valid_format_with_path(self):
        """Test parsing with file path containing special characters."""
        result = parse_synctex_forward("10:20:/path/to/file.tex")
        assert result == (10, 20, "/path/to/file.tex")

    def test_invalid_format_missing_parts(self):
        """Test that missing parts raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_synctex_forward("42:5")
        assert "Invalid synctex format" in str(exc_info.value)

    def test_invalid_format_too_many_parts(self):
        """Test format with too many colons raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_synctex_forward("42:5:file:extra")
        assert "Invalid synctex format" in str(exc_info.value)

    def test_invalid_line_number(self):
        """Test that non-numeric line raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_synctex_forward("abc:5:chapter.tex")
        assert "Line and column must be integers" in str(exc_info.value)

    def test_invalid_column_number(self):
        """Test that non-numeric column raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_synctex_forward("42:xyz:chapter.tex")
        assert "Line and column must be integers" in str(exc_info.value)


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
        
    def test_custom_port_with_http(self):
        """Test custom port with HTTP protocol."""
        url = get_server_url(3000, use_http=True)
        assert url == "http://localhost:3000"

    def test_high_number_port(self):
        """Test with high-numbered port."""
        url = get_server_url(65000)
        assert url == "https://localhost:65000"
