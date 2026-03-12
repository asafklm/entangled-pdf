"""Unit tests for pdfserver/sync.py client functions.

Tests the pdf-server sync CLI client functions without requiring a running server.
Uses mocking to verify correct HTTP requests are constructed.
"""

import json
import ssl
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from pdfserver.sync import (
    create_ssl_context,
    forward_search,
    load_pdf,
    parse_synctex_forward,
    send_request,
)
from pdfserver.cli import main


class TestCreateSslContext:
    """Test SSL context creation for self-signed certificates."""

    def test_creates_context_with_cert_none_verification(self):
        """Test that SSL context allows self-signed certificates."""
        context = create_ssl_context()
        assert isinstance(context, ssl.SSLContext)
        assert context.check_hostname is False
        assert context.verify_mode == ssl.CERT_NONE


class TestSendRequest:
    """Test HTTP/HTTPS request sending."""

    def test_send_request_with_https(self):
        """Test sending request over HTTPS."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "success"}'

        with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            result = send_request("GET", "/test", 8431)

            assert result == {"status": "success"}
            mock_urlopen.assert_called_once()
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            assert request.full_url == "https://localhost:8431/test"

    def test_send_request_with_http(self):
        """Test sending request over HTTP."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "ok"}'

        with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            result = send_request("GET", "/api", 8080, use_http=True)

            assert result == {"status": "ok"}
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            assert request.full_url == "http://localhost:8080/api"

    def test_send_request_with_api_key(self):
        """Test that API key is added to headers."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{}'

        with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            send_request("GET", "/test", 8431, api_key="secret123")

            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            assert request.headers["X-api-key"] == "secret123"

    def test_send_request_with_json_data(self):
        """Test sending JSON data in request body."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"received": true}'
        test_data = {"pdf_path": "/path/to/file.pdf"}

        with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            result = send_request("POST", "/api/load-pdf", 8431, data=test_data)

            assert result == {"received": True}
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            assert request.data == json.dumps(test_data).encode('utf-8')
            assert request.headers["Content-type"] == "application/json"

    def test_send_request_authentication_error(self):
        """Test handling of 403 authentication error."""
        # Create a proper mock HTTPError
        def mock_read():
            return b'{"detail": "Unauthorized"}'
        
        mock_error = HTTPError(
            url='https://localhost:8431/test',
            code=403,
            msg='Forbidden',
            hdrs={},
            fp=None
        )
        mock_error.read = mock_read

        with patch('urllib.request.urlopen', side_effect=mock_error):
            with pytest.raises(Exception) as exc_info:
                send_request("GET", "/test", 8431)

            assert "Authentication failed" in str(exc_info.value)
            assert "PDF_SERVER_API_KEY" in str(exc_info.value)

    def test_send_request_other_http_error(self):
        """Test handling of other HTTP errors."""
        # Create a proper mock HTTPError
        def mock_read():
            return b'{"detail": "Server error"}'
        
        mock_error = HTTPError(
            url='https://localhost:8431/test',
            code=500,
            msg='Internal Server Error',
            hdrs={},
            fp=None
        )
        mock_error.read = mock_read

        with patch('urllib.request.urlopen', side_effect=mock_error):
            with pytest.raises(Exception) as exc_info:
                send_request("GET", "/test", 8431)

            assert "HTTP 500" in str(exc_info.value)


class TestLoadPdfFieldName:
    """Test that load_pdf sends correct field names to server."""

    def test_load_pdf_sends_pdf_path_not_pdf_file(self, tmp_path):
        """Verify load_pdf sends 'pdf_path' field, not 'pdf_file'."""
        # Create a temporary PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")

        with patch('pdfserver.sync.send_request') as mock_send:
            mock_send.return_value = {"status": "success"}

            # Call load_pdf
            load_pdf(pdf_file, port=8431, api_key="test-key")

            # Verify send_request was called with correct field name
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1] if mock_send.call_args[1] else mock_send.call_args.kwargs

            # The data parameter should contain 'pdf_path', not 'pdf_file'
            data = call_kwargs.get('data')
            assert data is not None, "data parameter should be passed to send_request"
            assert 'pdf_path' in data, \
                f"load_pdf should send 'pdf_path' field, got: {list(data.keys())}"
            assert 'pdf_file' not in data, \
                f"load_pdf should NOT send 'pdf_file' field, got: {list(data.keys())}"
            assert data['pdf_path'] == str(pdf_file)

    def test_load_pdf_resolves_relative_path(self, tmp_path):
        """Test that load_pdf resolves relative paths to absolute."""
        # Create a temporary PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        rel_path = Path("test.pdf")

        with patch('pdfserver.sync.send_request') as mock_send:
            mock_send.return_value = {"status": "success"}

            # Change to temp directory and use relative path
            import os
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_path)
                load_pdf(rel_path, port=8431, api_key="test-key")

                # Verify the path was resolved to absolute
                call_kwargs = mock_send.call_args[1] if mock_send.call_args[1] else mock_send.call_args.kwargs
                data = call_kwargs.get('data')
                sent_path = Path(data['pdf_path'])
                assert sent_path.is_absolute(), f"Path should be absolute, got: {sent_path}"
                assert sent_path == pdf_file.resolve()
            finally:
                os.chdir(original_cwd)

    def test_load_pdf_raises_file_not_found(self, tmp_path):
        """Test that load_pdf raises FileNotFoundError for nonexistent file."""
        nonexistent = tmp_path / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError) as exc_info:
            load_pdf(nonexistent, port=8431)

        assert str(nonexistent) in str(exc_info.value)


class TestLoadPdfUsesCorrectEndpoint:
    """Test that load_pdf calls the correct endpoint."""

    def test_load_pdf_uses_correct_endpoint_and_method(self, tmp_path):
        """Verify load_pdf uses POST /api/load-pdf."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")

        with patch('pdfserver.sync.send_request') as mock_send:
            mock_send.return_value = {"status": "success"}

            load_pdf(pdf_file, port=8431, api_key="test-key")

            mock_send.assert_called_once()
            call_args = mock_send.call_args
            positional_args = call_args[0]
            
            # Check positional arguments
            assert positional_args[0] == "POST", f"Expected POST, got: {positional_args[0]}"
            assert positional_args[1] == "/api/load-pdf", f"Expected /api/load-pdf, got: {positional_args[1]}"
            assert positional_args[2] == 8431, f"Expected port 8431, got: {positional_args[2]}"


class TestForwardSearch:
    """Test forward search functionality."""

    def test_forward_search_sends_correct_data(self):
        """Test that forward_search sends correct data structure."""
        with patch('pdfserver.sync.send_request') as mock_send:
            mock_send.return_value = {"status": "success"}

            forward_search(
                line=42,
                column=5,
                tex_file="chapter.tex",
                port=8431,
                api_key="test-key"
            )

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1] if mock_send.call_args[1] else mock_send.call_args.kwargs

            # Check the data sent
            data = call_kwargs.get('data')
            assert data is not None
            assert data["page"] == 42  # Server uses line as page
            assert data["column"] == 5
            assert data["tex_file"] == "chapter.tex"

    def test_forward_search_uses_webhook_endpoint(self):
        """Test that forward_search uses /webhook/update endpoint."""
        with patch('pdfserver.sync.send_request') as mock_send:
            mock_send.return_value = {"status": "success"}

            forward_search(10, 0, "main.tex", 8431)

            call_args = mock_send.call_args
            positional_args = call_args[0]
            assert positional_args[1] == "/webhook/update"


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
        """Test parsing with file path containing colons (edge case)."""
        result = parse_synctex_forward("10:20:/path/to/file.tex")
        assert result == (10, 20, "/path/to/file.tex")

    def test_invalid_format_missing_parts(self):
        """Test that missing parts raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_synctex_forward("42:5")
        assert "Invalid synctex format" in str(exc_info.value)

    def test_invalid_format_too_many_parts(self):
        """Test format with too many colons."""
        # The actual implementation splits by all colons, so "42:5:file:extra" 
        # would have 4 parts and fail
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

    def test_main_exits_without_api_key(self, tmp_path, monkeypatch):
        """Test that main exits with error if no API key provided."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")

        # Clear environment variable
        monkeypatch.delenv("PDF_SERVER_API_KEY", raising=False)

        with patch('sys.argv', ['pdf-server', 'sync', str(pdf_file)]):
            result = main()
            assert result == 1

    def test_main_with_api_key_from_env(self, tmp_path, monkeypatch):
        """Test that main accepts API key from environment."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")

        monkeypatch.setenv("PDF_SERVER_API_KEY", "test-key")

        with patch('pdfserver.cli.load_pdf') as mock_load:
            mock_load.return_value = {"pdf_file": str(pdf_file)}

            with patch('sys.argv', ['pdf-server', 'sync', str(pdf_file)]):
                result = main()
                assert result == 0
                mock_load.assert_called_once()

    def test_main_with_api_key_from_flag(self, tmp_path):
        """Test that main accepts API key from --api-key flag."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")

        with patch('pdfserver.cli.load_pdf') as mock_load:
            mock_load.return_value = {"pdf_file": str(pdf_file)}

            with patch('sys.argv', ['pdf-server', 'sync', '--api-key', 'flag-key', str(pdf_file)]):
                result = main()
                assert result == 0
                mock_load.assert_called_once()
                call_kwargs = mock_load.call_args.kwargs
                assert call_kwargs['api_key'] == 'flag-key'
                assert call_kwargs['use_http'] is False

    def test_main_with_port_flag(self, tmp_path, monkeypatch):
        """Test that main accepts custom port from --port flag."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")

        monkeypatch.setenv("PDF_SERVER_API_KEY", "test-key")

        with patch('pdfserver.cli.load_pdf') as mock_load:
            mock_load.return_value = {"pdf_file": str(pdf_file)}

            with patch('sys.argv', ['pdf-server', 'sync', '--port', '9000', str(pdf_file)]):
                result = main()
                assert result == 0
                mock_load.assert_called_once()
                call_args = mock_load.call_args.args
                call_kwargs = mock_load.call_args.kwargs
                assert call_args[1] == 9000  # port argument
                assert call_kwargs['api_key'] == 'test-key'
                assert call_kwargs['use_http'] is False

    def test_main_with_http_flag(self, tmp_path, monkeypatch):
        """Test that main accepts --http flag."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")

        monkeypatch.setenv("PDF_SERVER_API_KEY", "test-key")

        with patch('pdfserver.cli.load_pdf') as mock_load:
            mock_load.return_value = {"pdf_file": str(pdf_file)}

            with patch('sys.argv', ['pdf-server', 'sync', '--http', str(pdf_file)]):
                result = main()
                assert result == 0
                mock_load.assert_called_once()
                call_kwargs = mock_load.call_args.kwargs
                assert call_kwargs['use_http'] is True

    def test_main_with_synctex_forward(self, tmp_path, monkeypatch):
        """Test that main accepts synctex info as positional argument."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")

        monkeypatch.setenv("PDF_SERVER_API_KEY", "test-key")

        with patch('pdfserver.cli.load_pdf') as mock_load, \
             patch('pdfserver.cli.forward_search') as mock_forward:
            mock_load.return_value = {"pdf_file": str(pdf_file)}
            mock_forward.return_value = {"status": "success"}

            with patch('sys.argv', [
                'pdf-server',
                'sync',
                str(pdf_file),
                '42:5:chapter.tex'
            ]):
                result = main()
                assert result == 0
                mock_forward.assert_called_once()
                call_args = mock_forward.call_args.args
                call_kwargs = mock_forward.call_args.kwargs
                assert call_args[0] == 42  # line
                assert call_args[1] == 5   # column
                assert call_args[2] == 'chapter.tex'  # tex_file
                assert call_args[3] == 8431  # port

    def test_main_handles_file_not_found(self, tmp_path, monkeypatch):
        """Test that main handles FileNotFoundError gracefully."""
        nonexistent = tmp_path / "nonexistent.pdf"

        monkeypatch.setenv("PDF_SERVER_API_KEY", "test-key")

        with patch('sys.argv', ['pdf-server', 'sync', str(nonexistent)]):
            result = main()
            assert result == 1

    def test_main_handles_other_exceptions(self, tmp_path, monkeypatch):
        """Test that main handles general exceptions gracefully."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")

        monkeypatch.setenv("PDF_SERVER_API_KEY", "test-key")

        with patch('pdfserver.cli.load_pdf', side_effect=Exception("Network error")):
            with patch('sys.argv', ['pdf-server', 'sync', str(pdf_file)]):
                result = main()
                assert result == 1

    def test_main_verbose_output(self, tmp_path, monkeypatch, capsys):
        """Test that --verbose flag produces output."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")

        monkeypatch.setenv("PDF_SERVER_API_KEY", "test-key")

        with patch('pdfserver.cli.load_pdf') as mock_load:
            mock_load.return_value = {"pdf_file": str(pdf_file), "status": "loaded"}

            with patch('sys.argv', ['pdf-server', 'sync', '-v', str(pdf_file)]):
                result = main()
                captured = capsys.readouterr()
                assert result == 0
                assert "Loading PDF" in captured.out or "Server response" in captured.out


class TestIntegrationBetweenFunctions:
    """Test that functions work correctly together."""

    def test_load_pdf_integration_with_send_request(self, tmp_path):
        """Integration test: load_pdf -> send_request with mocked URL open."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "status": "success",
            "pdf_file": str(pdf_file),
            "changed": True
        }).encode('utf-8')

        with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            result = load_pdf(pdf_file, port=8431, api_key="test-key")

            assert result["status"] == "success"
            mock_urlopen.assert_called_once()
            
            # Verify the request was constructed correctly
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            assert request.full_url == "https://localhost:8431/api/load-pdf"
            assert request.method == "POST"
            assert request.headers["X-api-key"] == "test-key"
            
            # Verify the request body
            sent_data = json.loads(request.data.decode('utf-8'))
            assert sent_data['pdf_path'] == str(pdf_file)

    def test_forward_search_integration_with_send_request(self):
        """Integration test: forward_search -> send_request with mocked URL open."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "status": "success",
            "page": 42,
            "y": 500.0
        }).encode('utf-8')

        with patch('urllib.request.urlopen', return_value=mock_response) as mock_urlopen:
            result = forward_search(
                line=42,
                column=5,
                tex_file="chapter.tex",
                port=8431,
                api_key="test-key"
            )

            assert result["status"] == "success"
            mock_urlopen.assert_called_once()
            
            # Verify the request
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            assert request.full_url == "https://localhost:8431/webhook/update"
            
            sent_data = json.loads(request.data.decode('utf-8'))
            assert sent_data['page'] == 42
            assert sent_data['column'] == 5
            assert sent_data['tex_file'] == "chapter.tex"
