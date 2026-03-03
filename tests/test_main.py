"""Tests for main application entry point."""

import pytest
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI

from main import create_app, parse_args, main


@pytest.fixture
def mock_settings(tmp_path):
    """Create mock settings for testing."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_text("dummy content")
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    
    from src.config import Settings
    return Settings(
        pdf_file=pdf_file,
        port=8080,
        secret="test-secret",
        host="127.0.0.1",
        static_dir=static_dir
    )


class TestCreateApp:
    """Test suite for create_app function."""
    
    def test_create_app_returns_fastapi_instance(self, mock_settings):
        """Test that create_app returns a FastAPI instance."""
        with patch("main.static_files.setup_static_files"):
            with patch("main.init_settings", return_value=mock_settings):
                app = create_app()
                assert isinstance(app, FastAPI)
    
    def test_create_app_has_correct_title(self, mock_settings):
        """Test that app has correct title and description."""
        with patch("main.static_files.setup_static_files"):
            with patch("main.init_settings", return_value=mock_settings):
                app = create_app()
                assert app.title == "PdfServer"
                assert "PDF synchronization" in app.description
    
    def test_create_app_includes_view_router(self, mock_settings):
        """Test that view router is included."""
        with patch("main.static_files.setup_static_files"):
            with patch("main.init_settings", return_value=mock_settings):
                app = create_app()
                routes = [str(route) for route in app.routes]
                assert any("/view" in route for route in routes)
    
    def test_create_app_includes_pdf_router(self, mock_settings):
        """Test that PDF router is included."""
        with patch("main.static_files.setup_static_files"):
            with patch("main.init_settings", return_value=mock_settings):
                app = create_app()
                routes = [str(route) for route in app.routes]
                assert any("/get-pdf" in route for route in routes)
    
    def test_create_app_includes_state_router(self, mock_settings):
        """Test that state router is included."""
        with patch("main.static_files.setup_static_files"):
            with patch("main.init_settings", return_value=mock_settings):
                app = create_app()
                routes = [str(route) for route in app.routes]
                assert any("/state" in route for route in routes)
    
    def test_create_app_includes_webhook_router(self, mock_settings):
        """Test that webhook router is included."""
        with patch("main.static_files.setup_static_files"):
            with patch("main.init_settings", return_value=mock_settings):
                app = create_app()
                routes = [str(route) for route in app.routes]
                assert any("/webhook" in route for route in routes)
    
    def test_create_app_includes_websocket_router(self, mock_settings):
        """Test that WebSocket router is included."""
        with patch("main.static_files.setup_static_files"):
            with patch("main.init_settings", return_value=mock_settings):
                app = create_app()
                routes = [str(route) for route in app.routes]
                assert any("/ws" in route for route in routes)
    
    def test_create_app_setup_static_files(self, mock_settings):
        """Test that static files are configured."""
        with patch("main.static_files.setup_static_files") as mock_setup:
            with patch("main.init_settings", return_value=mock_settings):
                app = create_app()
                mock_setup.assert_called_once_with(app)


class TestParseArgs:
    """Test suite for parse_args function."""
    
    def test_parse_args_pdf_file_optional(self):
        """Test that PDF file argument is now optional."""
        with patch.object(sys, "argv", ["main.py"]):
            args = parse_args()
            assert args.pdf_file is None
    
    def test_parse_args_pdf_file_provided(self):
        """Test parsing with PDF file argument."""
        with patch.object(sys, "argv", ["main.py", "document.pdf"]):
            args = parse_args()
            
            assert args.pdf_file == "document.pdf"
            assert args.port_arg is None
    
    def test_parse_args_port_arg_optional(self):
        """Test that port argument is optional."""
        with patch.object(sys, "argv", ["main.py", "doc.pdf"]):
            args = parse_args()
            
            assert args.port_arg is None
    
    def test_parse_args_port_format_parsing(self):
        """Test parsing port in format port=8001."""
        with patch.object(sys, "argv", ["main.py", "doc.pdf", "port=9000"]):
            args = parse_args()
            
            assert args.port_arg == "port=9000"
    
    def test_parse_args_invalid_port_format(self):
        """Test that invalid port format is still parsed (validation in main)."""
        with patch.object(sys, "argv", ["main.py", "doc.pdf", "invalid-port"]):
            args = parse_args()
            
            assert args.port_arg == "invalid-port"
    
    def test_parse_args_multiple_args(self):
        """Test parsing with all arguments."""
        with patch.object(sys, "argv", ["main.py", "thesis.pdf", "port=8080"]):
            args = parse_args()
            
            assert args.pdf_file == "thesis.pdf"
            assert args.port_arg == "port=8080"


class TestMain:
    """Test suite for main function."""
    
    def test_main_successful_startup(self, tmp_path):
        """Test successful application startup."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy content")
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        
        with patch.object(sys, "argv", ["main.py", str(pdf_file)]):
            with patch("main.uvicorn.run") as mock_run:
                with patch("main.init_settings") as mock_init:
                    from src.config import Settings
                    mock_settings = Settings(
                        pdf_file=pdf_file,
                        port=8431,
                        secret="test-secret",
                        host="0.0.0.0",
                        static_dir=static_dir
                    )
                    mock_init.return_value = mock_settings
                    
                    with patch("main.create_app") as mock_create:
                        mock_create.return_value = MagicMock()
                        
                        main()
                        
                        mock_init.assert_called_once()
                        mock_run.assert_called_once()
    
    def test_main_with_port_argument(self, tmp_path):
        """Test main with port argument."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy content")
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        
        with patch.object(sys, "argv", ["main.py", str(pdf_file), "port=9000"]):
            with patch("main.uvicorn.run"):
                with patch("main.init_settings") as mock_init:
                    from src.config import Settings
                    mock_settings = Settings(
                        pdf_file=pdf_file,
                        port=9000,
                        secret="test-secret",
                        host="0.0.0.0",
                        static_dir=static_dir
                    )
                    mock_init.return_value = mock_settings
                    
                    with patch("main.create_app"):
                        main()
                        
                        # Verify init_settings was called with port=9000
                        call_kwargs = mock_init.call_args[1]
                        assert call_kwargs["port"] == 9000
    
    def test_main_invalid_port_format(self, tmp_path, capsys):
        """Test main with invalid port format."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy content")
        
        with patch.object(sys, "argv", ["main.py", str(pdf_file), "invalid"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
    
    def test_main_missing_pdf_file(self, tmp_path, capsys):
        """Test main with non-existent PDF file."""
        pdf_file = tmp_path / "nonexistent.pdf"
        
        with patch.object(sys, "argv", ["main.py", str(pdf_file)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
    
    def test_main_uvicorn_configuration(self, tmp_path):
        """Test that uvicorn is configured correctly."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy content")
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        
        with patch.object(sys, "argv", ["main.py", str(pdf_file)]):
            with patch("main.uvicorn.run") as mock_run:
                with patch("main.init_settings") as mock_init:
                    from src.config import Settings
                    mock_settings = Settings(
                        pdf_file=pdf_file,
                        port=8080,
                        secret="test-secret",
                        host="127.0.0.1",
                        static_dir=static_dir
                    )
                    mock_init.return_value = mock_settings
                    
                    with patch("main.create_app") as mock_create:
                        mock_app = MagicMock()
                        mock_create.return_value = mock_app
                        
                        main()
                        
                        # Verify uvicorn.run was called with correct args
                        mock_run.assert_called_once()
                        call_args = mock_run.call_args
                        assert call_args[1]["host"] == "127.0.0.1"
                        assert call_args[1]["port"] == 8080
