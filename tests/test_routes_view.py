"""Tests for view endpoint."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.routes import view as view_route
from src.config import Settings


@pytest.fixture
def mock_settings(tmp_path):
    """Create mock settings with template directory."""
    pdf_file = tmp_path / "document.pdf"
    pdf_file.write_text("dummy content")
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    
    # Create viewer.html template
    viewer_html = static_dir / "viewer.html"
    viewer_html.write_text("""<!DOCTYPE html>
<html>
<head><title>{{ filename }}</title></head>
<body>
    <p>Port: {{ port }}</p>
    <p>File: {{ filename }}</p>
</body>
</html>""")
    
    return Settings(
        pdf_file=pdf_file,
        port=8080,
        secret="test-secret",
        host="127.0.0.1",
        static_dir=static_dir
    )


@pytest.fixture
def client(mock_settings):
    """Create test client with mocked settings."""
    app = FastAPI()
    app.include_router(view_route.router)
    
    with patch("src.routes.view.get_settings", return_value=mock_settings):
        with patch.object(view_route, "_templates", None):  # Reset templates cache
            yield TestClient(app)


class TestViewPage:
    """Test suite for GET /view endpoint."""
    
    def test_view_page_returns_html(self, client):
        """Test that endpoint returns HTML response."""
        response = client.get("/view")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_view_page_contains_filename(self, client, mock_settings):
        """Test that HTML contains the PDF filename."""
        response = client.get("/view")
        
        assert response.status_code == 200
        assert "document.pdf" in response.text
    
    def test_view_page_contains_port(self, client, mock_settings):
        """Test that HTML contains the port number."""
        response = client.get("/view")
        
        assert response.status_code == 200
        assert "8080" in response.text
    
    def test_view_page_uses_jinja2_template(self, client):
        """Test that Jinja2 template rendering is used."""
        response = client.get("/view")
        
        assert response.status_code == 200
        # Template variables should be substituted
        assert "{{" not in response.text
        assert "}}" not in response.text
    
    def test_view_page_different_filename(self, tmp_path):
        """Test with different PDF filename."""
        pdf_file = tmp_path / "thesis.pdf"
        pdf_file.write_text("dummy content")
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        
        viewer_html = static_dir / "viewer.html"
        viewer_html.write_text("<html><body>{{ filename }}</body></html>")
        
        settings = Settings(
            pdf_file=pdf_file,
            port=9000,
            secret="test-secret",
            host="127.0.0.1",
            static_dir=static_dir
        )
        
        app = FastAPI()
        app.include_router(view_route.router)
        
        with patch("src.routes.view.get_settings", return_value=settings):
            with patch.object(view_route, "_templates", None):
                client = TestClient(app)
                response = client.get("/view")
                
                assert response.status_code == 200
                assert "thesis.pdf" in response.text
    
    def test_view_page_different_port(self, tmp_path):
        """Test with different port number."""
        pdf_file = tmp_path / "doc.pdf"
        pdf_file.write_text("dummy content")
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        
        viewer_html = static_dir / "viewer.html"
        viewer_html.write_text("<html><body>{{ port }}</body></html>")
        
        settings = Settings(
            pdf_file=pdf_file,
            port=3000,
            secret="test-secret",
            host="127.0.0.1",
            static_dir=static_dir
        )
        
        app = FastAPI()
        app.include_router(view_route.router)
        
        with patch("src.routes.view.get_settings", return_value=settings):
            with patch.object(view_route, "_templates", None):
                client = TestClient(app)
                response = client.get("/view")
                
                assert response.status_code == 200
                assert "3000" in response.text
    
    def test_view_page_template_not_found(self, tmp_path):
        """Test handling when template file is missing."""
        pdf_file = tmp_path / "doc.pdf"
        pdf_file.write_text("dummy content")
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        # Don't create viewer.html
        
        settings = Settings(
            pdf_file=pdf_file,
            port=8080,
            secret="test-secret",
            host="127.0.0.1",
            static_dir=static_dir
        )
        
        app = FastAPI()
        app.include_router(view_route.router)
        
        with patch("src.routes.view.get_settings", return_value=settings):
            with patch.object(view_route, "_templates", None):
                client = TestClient(app)
                # TemplateNotFound exception is raised and converted to 500 error
                with pytest.raises(Exception):
                    client.get("/view")
    
    def test_view_page_complex_template(self, tmp_path):
        """Test with more complex template content."""
        pdf_file = tmp_path / "complex.pdf"
        pdf_file.write_text("dummy content")
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        
        viewer_html = static_dir / "viewer.html"
        viewer_html.write_text("""<!DOCTYPE html>
<html>
<head>
    <title>{{ filename }} - Viewer</title>
    <script>
        window.PDF_CONFIG = {
            port: {{ port }},
            filename: "{{ filename }}"
        };
    </script>
</head>
<body>
    <h1>Viewing: {{ filename }}</h1>
    <p>Server port: {{ port }}</p>
</body>
</html>""")
        
        settings = Settings(
            pdf_file=pdf_file,
            port=7777,
            secret="test-secret",
            host="127.0.0.1",
            static_dir=static_dir
        )
        
        app = FastAPI()
        app.include_router(view_route.router)
        
        with patch("src.routes.view.get_settings", return_value=settings):
            with patch.object(view_route, "_templates", None):
                client = TestClient(app)
                response = client.get("/view")
                
                assert response.status_code == 200
                assert "complex.pdf" in response.text
                assert "7777" in response.text
                assert "{{" not in response.text  # All variables substituted
