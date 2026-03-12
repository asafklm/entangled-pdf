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
    
    from pdfserver.config import Settings
    return Settings(
        pdf_file=pdf_file,
        port=8080,
        api_key="test-secret",
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
    
    def test_parse_args_no_arguments(self):
        """Test parsing with no arguments (all optional)."""
        with patch.object(sys, "argv", ["main.py"]):
            args = parse_args()
            assert args.port is None
            assert args.http is False
            assert args.inverse_search_command is None
            assert args.inverse_search_nvim is False
            assert args.inverse_search_vim is False
            assert args.verbose is False
    
    def test_parse_args_port_provided(self):
        """Test parsing with --port argument."""
        with patch.object(sys, "argv", ["main.py", "--port", "9000"]):
            args = parse_args()
            assert args.port == 9000
    
    def test_parse_args_http_mode(self):
        """Test parsing with --http flag."""
        with patch.object(sys, "argv", ["main.py", "--http"]):
            args = parse_args()
            assert args.http is True
    
    def test_parse_args_inverse_search_nvim(self):
        """Test parsing with --inverse-search-nvim flag."""
        with patch.object(sys, "argv", ["main.py", "--inverse-search-nvim"]):
            args = parse_args()
            assert args.inverse_search_nvim is True
    
    def test_parse_args_inverse_search_vim(self):
        """Test parsing with --inverse-search-vim flag."""
        with patch.object(sys, "argv", ["main.py", "--inverse-search-vim"]):
            args = parse_args()
            assert args.inverse_search_vim is True
    
    def test_parse_args_inverse_search_command(self):
        """Test parsing with --inverse-search-command argument."""
        with patch.object(sys, "argv", ["main.py", "--inverse-search-command", "nvr --remote-silent +%{line} %{file}"]):
            args = parse_args()
            assert args.inverse_search_command == "nvr --remote-silent +%{line} %{file}"
    
    def test_parse_args_verbose(self):
        """Test parsing with --verbose flag."""
        with patch.object(sys, "argv", ["main.py", "--verbose"]):
            args = parse_args()
            assert args.verbose is True
    
    def test_parse_args_multiple_flags(self):
        """Test parsing with multiple arguments."""
        with patch.object(sys, "argv", ["main.py", "--port", "8080", "--inverse-search-nvim", "--verbose"]):
            args = parse_args()
            assert args.port == 8080
            assert args.inverse_search_nvim is True
            assert args.verbose is True


class TestMain:
    """Test suite for main function."""
    
    def test_main_successful_startup(self, tmp_path):
        """Test successful application startup."""
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        
        with patch.object(sys, "argv", ["main.py"]):
            with patch("main.uvicorn.run") as mock_run:
                with patch("main.init_settings") as mock_init:
                    from pdfserver.config import Settings
                    mock_settings = Settings(
                        pdf_file=None,  # No PDF file in new architecture
                        port=8431,
                        api_key="test-secret",
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
        """Test main with --port argument."""
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        
        with patch.object(sys, "argv", ["main.py", "--port", "9000"]):
            with patch("main.uvicorn.run"):
                with patch("main.init_settings") as mock_init:
                    from pdfserver.config import Settings
                    mock_settings = Settings(
                        pdf_file=None,
                        port=9000,
                        api_key="test-secret",
                        host="0.0.0.0",
                        static_dir=static_dir
                    )
                    mock_init.return_value = mock_settings
                    
                    with patch("main.create_app"):
                        main()
                        
                        # Verify init_settings was called with port=9000
                        call_kwargs = mock_init.call_args[1]
                        assert call_kwargs["port"] == 9000
    
    def test_main_with_inverse_search_nvim(self, tmp_path):
        """Test main with --inverse-search-nvim flag."""
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        
        with patch.object(sys, "argv", ["main.py", "--inverse-search-nvim"]):
            with patch("main.uvicorn.run"):
                with patch("main.init_settings") as mock_init:
                    from pdfserver.config import Settings
                    mock_settings = Settings(
                        pdf_file=None,
                        port=8431,
                        api_key="test-secret",
                        host="0.0.0.0",
                        static_dir=static_dir,
                        use_https=True  # Required for inverse search
                    )
                    mock_init.return_value = mock_settings
                    
                    with patch("main.create_app"):
                        with patch("main.validate_ssl_config", return_value={"ssl_keyfile": "test", "ssl_certfile": "test"}):
                            with patch("main.pdf_state") as mock_state:
                                main()
                                # Verify inverse search was enabled
                                assert mock_state.inverse_search_enabled is True
    
    def test_main_uvicorn_configuration(self, tmp_path):
        """Test that uvicorn is configured correctly."""
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        
        with patch.object(sys, "argv", ["main.py", "--port", "8080"]):
            with patch("main.uvicorn.run") as mock_run:
                with patch("main.init_settings") as mock_init:
                    from pdfserver.config import Settings
                    mock_settings = Settings(
                        pdf_file=None,
                        port=8080,
                        api_key="test-secret",
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
