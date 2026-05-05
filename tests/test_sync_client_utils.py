"""Unit tests for entangle-pdf sync client utility functions.

Tests the utility functions from entangledpdf/sync that support the 
CLI client functionality (argument parsing, socket path, etc.).
"""

import pytest
from pathlib import Path

from entangledpdf.sync import parse_synctex_forward, get_default_socket_path
from entangledpdf.socket_path import get_socket_path


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


class TestGetDefaultSocketPath:
    """Test socket path retrieval."""

    def test_returns_path_object(self):
        """Test that get_default_socket_path returns a Path."""
        path = get_default_socket_path()
        assert isinstance(path, Path)

    def test_returns_absolute_path(self):
        """Test that socket path is absolute."""
        path = get_default_socket_path()
        assert path.is_absolute()

    def test_contains_socket_filename(self):
        """Test that path ends with server.sock."""
        path = get_default_socket_path()
        assert path.name == "server.sock"

    def test_matches_get_socket_path(self):
        """Test that get_default_socket_path matches get_socket_path."""
        from_default = get_default_socket_path()
        from_module = get_socket_path()
        assert from_default == from_module
