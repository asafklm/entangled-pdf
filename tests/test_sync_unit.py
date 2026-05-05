"""Unit tests for entangledpdf/sync.py client functions.

Tests the entangle-pdf sync CLI client functions without requiring a running server.
Uses mocking to verify correct HTTP requests are constructed over Unix sockets.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from entangledpdf.sync import (
    forward_search,
    load_pdf,
    parse_synctex_forward,
    send_request,
    UnixHTTPConnection,
    get_default_socket_path,
)
from entangledpdf.cli import main


class TestUnixHTTPConnection:
    """Test Unix domain socket HTTP connection."""

    def test_connection_creation(self, tmp_path):
        """Test that UnixHTTPConnection initializes with socket path."""
        socket_path = str(tmp_path / "test.sock")
        conn = UnixHTTPConnection(socket_path)
        assert conn.socket_path == socket_path


class TestSendRequest:
    """Test HTTP request sending over Unix socket."""

    def test_send_request_get(self, tmp_path):
        """Test sending GET request over Unix socket."""
        socket_path = tmp_path / "test.sock"
        
        # Create a mock socket and response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"status": "success"}'
        
        with patch('http.client.HTTPResponse', return_value=mock_response):
            with patch.object(UnixHTTPConnection, 'connect') as mock_connect:
                with patch.object(UnixHTTPConnection, 'request') as mock_request:
                    with patch.object(UnixHTTPConnection, 'getresponse', return_value=mock_response):
                        result = send_request("GET", "/test", socket_path)
                        
                        assert result == {"status": "success"}
                        mock_request.assert_called_once()
                        call_args = mock_request.call_args
                        assert call_args[0][0] == "GET"
                        assert call_args[0][1] == "/test"

    def test_send_request_with_json_data(self, tmp_path):
        """Test sending JSON data in request body."""
        socket_path = tmp_path / "test.sock"
        test_data = {"pdf_path": "/path/to/file.pdf"}
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"received": true}'
        
        with patch.object(UnixHTTPConnection, 'connect'):
            with patch.object(UnixHTTPConnection, 'request') as mock_request:
                with patch.object(UnixHTTPConnection, 'getresponse', return_value=mock_response):
                    result = send_request("POST", "/api/load-pdf", socket_path, data=test_data)
                    
                    assert result == {"received": True}
                    mock_request.assert_called_once()
                    call_args = mock_request.call_args
                    # Check method, path, body, headers
                    assert call_args[0][0] == "POST"
                    assert call_args[0][1] == "/api/load-pdf"
                    assert json.loads(call_args[1]['body']) == test_data
                    assert call_args[1]['headers']["Content-Type"] == "application/json"

    def test_send_request_http_error(self, tmp_path):
        """Test handling of HTTP errors."""
        socket_path = tmp_path / "test.sock"
        
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.read.return_value = b'Server error'
        
        with patch.object(UnixHTTPConnection, 'connect'):
            with patch.object(UnixHTTPConnection, 'request'):
                with patch.object(UnixHTTPConnection, 'getresponse', return_value=mock_response):
                    with pytest.raises(Exception) as exc_info:
                        send_request("GET", "/test", socket_path)
                    
                    assert "HTTP 500" in str(exc_info.value)


class TestLoadPdf:
    """Test PDF loading functionality."""

    def test_load_pdf_sends_correct_data(self, tmp_path):
        """Verify load_pdf sends 'pdf_path' field."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        socket_path = tmp_path / "test.sock"
        
        with patch('entangledpdf.sync.send_request') as mock_send:
            mock_send.return_value = {"status": "success"}
            
            load_pdf(pdf_file, socket_path)
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            # call_args[0] is positional args, call_args[1] is keyword args
            if call_args[0]:
                # Positional args: (method, path, socket_path, data)
                assert call_args[0][0] == "POST"
                assert call_args[0][1] == "/api/load-pdf"
                assert call_args[0][2] == socket_path
                data = call_args[0][3] if len(call_args[0]) > 3 else None
            else:
                # Keyword args
                kwargs = call_args[1]
                assert kwargs.get('method') == "POST"
                assert kwargs.get('path') == "/api/load-pdf"
                assert kwargs.get('socket_path') == socket_path
                data = kwargs.get('data')
            
            assert data is not None
            assert 'pdf_path' in data
            assert data['pdf_path'] == str(pdf_file.resolve())

    def test_load_pdf_resolves_relative_path(self, tmp_path):
        """Test that load_pdf resolves relative paths to absolute."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        socket_path = tmp_path / "test.sock"
        rel_path = Path("test.pdf")
        
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            with patch('entangledpdf.sync.send_request') as mock_send:
                mock_send.return_value = {"status": "success"}
                load_pdf(rel_path, socket_path)
                
                call_args = mock_send.call_args
                # Get data from positional or keyword args
                if call_args[0] and len(call_args[0]) > 3:
                    data = call_args[0][3]
                else:
                    data = call_args[1].get('data') if call_args[1] else None
                
                assert data is not None
                sent_path = Path(data['pdf_path'])
                assert sent_path.is_absolute()
                assert sent_path == pdf_file.resolve()
        finally:
            os.chdir(original_cwd)

    def test_load_pdf_raises_file_not_found(self, tmp_path):
        """Test that load_pdf raises FileNotFoundError for nonexistent file."""
        nonexistent = tmp_path / "nonexistent.pdf"
        socket_path = tmp_path / "test.sock"
        
        with pytest.raises(FileNotFoundError) as exc_info:
            load_pdf(nonexistent, socket_path)
        
        assert str(nonexistent) in str(exc_info.value)

    def test_load_pdf_uses_default_socket_path(self, tmp_path):
        """Test that load_pdf uses default socket path when not specified."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        with patch('entangledpdf.sync.send_request') as mock_send:
            mock_send.return_value = {"status": "success"}
            load_pdf(pdf_file)
            
            call_args = mock_send.call_args
            socket_path_arg = call_args[0][2]
            assert socket_path_arg == get_default_socket_path()


class TestForwardSearch:
    """Test forward search functionality."""

    def test_forward_search_sends_correct_data(self, tmp_path):
        """Test that forward_search sends correct data structure."""
        socket_path = tmp_path / "test.sock"
        
        with patch('entangledpdf.sync.send_request') as mock_send:
            mock_send.return_value = {"status": "success"}
            
            forward_search(
                line=42,
                column=5,
                tex_file="chapter.tex",
                pdf_file="/path/to/document.pdf",
                socket_path=socket_path
            )
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            # Get data from positional or keyword args
            if call_args[0] and len(call_args[0]) > 3:
                data = call_args[0][3]
            else:
                data = call_args[1].get('data') if call_args[1] else None
            
            assert data is not None
            assert data["line"] == 42
            assert data["col"] == 5
            assert data["tex_file"] == "chapter.tex"

    def test_forward_search_uses_default_socket_path(self, tmp_path):
        """Test that forward_search uses default socket path when not specified."""
        with patch('entangledpdf.sync.send_request') as mock_send:
            mock_send.return_value = {"status": "success"}
            
            forward_search(10, 0, "main.tex", "/path/to/file.pdf")
            
            call_args = mock_send.call_args
            socket_path_arg = call_args[0][2]
            assert socket_path_arg == get_default_socket_path()


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
        """Test parsing with file path containing colons."""
        result = parse_synctex_forward("10:20:/path/to/file.tex")
        assert result == (10, 20, "/path/to/file.tex")

    def test_invalid_format_missing_parts(self):
        """Test that missing parts raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_synctex_forward("42:5")
        assert "Invalid synctex format" in str(exc_info.value)

    def test_invalid_format_too_many_parts(self):
        """Test format with too many colons."""
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


class TestMainArgumentParsing:
    """Test CLI argument parsing in main()."""

    def test_main_without_api_key_succeeds(self, tmp_path, monkeypatch):
        """Test that main succeeds without API key (uses Unix socket)."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        # Ensure no API key in environment
        monkeypatch.delenv("ENTANGLEDPDF_API_KEY", raising=False)
        
        with patch('entangledpdf.cli.load_pdf') as mock_load:
            mock_load.return_value = {"pdf_file": str(pdf_file)}
            
            with patch('sys.argv', ['entangle-pdf', 'sync', str(pdf_file)]):
                result = main()
                assert result == 0
                mock_load.assert_called_once()

    def test_main_with_socket_path_flag(self, tmp_path):
        """Test that main accepts custom socket path."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        custom_socket = tmp_path / "custom.sock"
        
        with patch('entangledpdf.cli.load_pdf') as mock_load:
            mock_load.return_value = {"pdf_file": str(pdf_file)}
            
            with patch('sys.argv', [
                'entangle-pdf', 
                'sync', 
                '--socket-path', str(custom_socket),
                str(pdf_file)
            ]):
                result = main()
                assert result == 0
                mock_load.assert_called_once()
                call_args = mock_load.call_args
                # Check positional args: load_pdf(pdf_file, socket_path)
                assert call_args[0][0] == pdf_file
                assert call_args[0][1] == custom_socket

    def test_main_with_synctex_forward(self, tmp_path, monkeypatch):
        """Test that main accepts synctex info as positional argument."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        # Create a tex file that actually exists
        tex_file = tmp_path / "chapter.tex"
        tex_file.write_text("\\documentclass{article}")
        
        with patch('entangledpdf.cli.load_pdf') as mock_load, \
             patch('entangledpdf.cli.forward_search') as mock_forward:
            mock_load.return_value = {"pdf_file": str(pdf_file)}
            mock_forward.return_value = {"status": "success"}
            
            with patch('sys.argv', [
                'entangle-pdf',
                'sync',
                str(pdf_file),
                f'42:5:{tex_file}'
            ]):
                result = main()
                assert result == 0
                mock_forward.assert_called_once()
                call_args = mock_forward.call_args.args
                assert call_args[0] == 42  # line
                assert call_args[1] == 5   # column
                assert call_args[2] == str(tex_file)  # tex_file
                assert call_args[3] == str(pdf_file)  # pdf_file

    def test_main_handles_file_not_found(self, tmp_path):
        """Test that main handles FileNotFoundError gracefully."""
        nonexistent = tmp_path / "nonexistent.pdf"
        
        with patch('sys.argv', ['entangle-pdf', 'sync', str(nonexistent)]):
            result = main()
            assert result == 1

    def test_main_handles_other_exceptions(self, tmp_path):
        """Test that main handles general exceptions gracefully."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        with patch('entangledpdf.cli.load_pdf', side_effect=Exception("Socket error")):
            with patch('sys.argv', ['entangle-pdf', 'sync', str(pdf_file)]):
                result = main()
                assert result == 1

    def test_main_verbose_output(self, tmp_path, capsys):
        """Test that --verbose flag produces output."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        with patch('entangledpdf.cli.load_pdf') as mock_load:
            mock_load.return_value = {"pdf_file": str(pdf_file), "status": "loaded"}
            
            with patch('sys.argv', ['entangle-pdf', 'sync', '-v', str(pdf_file)]):
                result = main()
                captured = capsys.readouterr()
                assert result == 0
                assert "Loading PDF" in captured.out


class TestIntegrationBetweenFunctions:
    """Test that functions work correctly together."""

    def test_load_pdf_integration_with_send_request(self, tmp_path):
        """Integration test: load_pdf -> send_request."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        socket_path = tmp_path / "test.sock"
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "status": "success",
            "pdf_file": str(pdf_file),
            "changed": True
        }).encode('utf-8')
        
        with patch.object(UnixHTTPConnection, 'connect'):
            with patch.object(UnixHTTPConnection, 'request') as mock_request:
                with patch.object(UnixHTTPConnection, 'getresponse', return_value=mock_response):
                    result = load_pdf(pdf_file, socket_path)
                    
                    assert result["status"] == "success"
                    mock_request.assert_called_once()
                    
                    # Verify request was constructed correctly
                    call_args = mock_request.call_args
                    assert call_args[0][0] == "POST"
                    assert call_args[0][1] == "/api/load-pdf"
                    assert json.loads(call_args[1]['body'])['pdf_path'] == str(pdf_file.resolve())

    def test_forward_search_integration_with_send_request(self, tmp_path):
        """Integration test: forward_search -> send_request."""
        socket_path = tmp_path / "test.sock"
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "status": "success",
            "page": 42,
            "y": 500.0
        }).encode('utf-8')
        
        with patch.object(UnixHTTPConnection, 'connect'):
            with patch.object(UnixHTTPConnection, 'request') as mock_request:
                with patch.object(UnixHTTPConnection, 'getresponse', return_value=mock_response):
                    result = forward_search(
                        line=42,
                        column=5,
                        tex_file="chapter.tex",
                        pdf_file="/path/to/document.pdf",
                        socket_path=socket_path
                    )
                    
                    assert result["status"] == "success"
                    mock_request.assert_called_once()
                    
                    # Verify request
                    call_args = mock_request.call_args
                    assert call_args[0][0] == "POST"
                    assert call_args[0][1] == "/webhook/update"
                    
                    sent_data = json.loads(call_args[1]['body'])
                    assert sent_data['line'] == 42
                    assert sent_data['col'] == 5
                    assert sent_data['tex_file'] == "chapter.tex"


class TestPatchPathValidation:
    """Validate that mock patch paths point to real modules."""
    
    def test_webhook_patch_path_exists(self):
        """Verify that entangledpdf.routes.webhook module exists."""
        try:
            import entangledpdf.routes.webhook
            assert hasattr(entangledpdf.routes.webhook, 'get_settings')
            assert hasattr(entangledpdf.routes.webhook, 'run_synctex_view')
        except ImportError:
            pytest.fail("entangledpdf.routes.webhook module not found")
    
    def test_config_patch_path_exists(self):
        """Verify that entangledpdf.config module exists."""
        try:
            import entangledpdf.config
            assert hasattr(entangledpdf.config, 'get_settings')
        except ImportError:
            pytest.fail("entangledpdf.config module not found")
    
    def test_connection_manager_patch_path_exists(self):
        """Verify that entangledpdf.connection_manager module exists."""
        try:
            import entangledpdf.connection_manager
            assert hasattr(entangledpdf.connection_manager, 'manager')
        except ImportError:
            pytest.fail("entangledpdf.connection_manager module not found")
