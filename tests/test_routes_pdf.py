"""Tests for PDF serving endpoint."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.routes import pdf as pdf_route
from src.config import Settings


@pytest.fixture
def mock_settings(tmp_path):
    """Create mock settings with PDF file."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_text("dummy pdf content for testing")
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    
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
    app.include_router(pdf_route.router)
    
    with patch("src.routes.pdf.get_settings", return_value=mock_settings):
        yield TestClient(app)


class TestGetPdf:
    """Test suite for GET /get-pdf endpoint."""
    
    def test_get_pdf_returns_file(self, client, mock_settings):
        """Test that endpoint returns the PDF file."""
        response = client.get("/get-pdf")
        
        assert response.status_code == 200
        assert len(response.content) > 0
    
    def test_get_pdf_correct_content_type(self, client):
        """Test that response has correct Content-Type header."""
        response = client.get("/get-pdf")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
    
    def test_get_pdf_correct_filename_header(self, client, mock_settings):
        """Test that response includes correct filename in Content-Disposition."""
        response = client.get("/get-pdf")
        
        assert response.status_code == 200
        # FastAPI FileResponse sets content-disposition with filename
        assert "content-disposition" in response.headers
        assert "test.pdf" in response.headers["content-disposition"]
    
    def test_get_pdf_file_content(self, client, mock_settings):
        """Test that returned content matches the PDF file."""
        expected_content = mock_settings.pdf_file.read_bytes()
        
        response = client.get("/get-pdf")
        
        assert response.status_code == 200
        assert response.content == expected_content
    
    def test_get_pdf_different_filenames(self, tmp_path):
        """Test that endpoint works with different PDF filenames."""
        pdf_file = tmp_path / "my-document.pdf"
        pdf_file.write_text("different content")
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        
        settings = Settings(
            pdf_file=pdf_file,
            port=8080,
            secret="test-secret",
            host="127.0.0.1",
            static_dir=static_dir
        )
        
        app = FastAPI()
        app.include_router(pdf_route.router)
        
        with patch("src.routes.pdf.get_settings", return_value=settings):
            client = TestClient(app)
            response = client.get("/get-pdf")
            
            assert response.status_code == 200
            assert "my-document.pdf" in response.headers["content-disposition"]
    
    def test_get_pdf_binary_content(self, tmp_path):
        """Test that binary PDF content is served correctly."""
        # Create a file with binary-like content
        pdf_file = tmp_path / "binary.pdf"
        binary_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n"
        pdf_file.write_bytes(binary_content)
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        
        settings = Settings(
            pdf_file=pdf_file,
            port=8080,
            secret="test-secret",
            host="127.0.0.1",
            static_dir=static_dir
        )
        
        app = FastAPI()
        app.include_router(pdf_route.router)
        
        with patch("src.routes.pdf.get_settings", return_value=settings):
            client = TestClient(app)
            response = client.get("/get-pdf")
            
            assert response.status_code == 200
            assert response.content == binary_content
    
    def test_get_pdf_empty_file(self, tmp_path):
        """Test handling of empty PDF file."""
        pdf_file = tmp_path / "empty.pdf"
        pdf_file.write_text("")
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        
        settings = Settings(
            pdf_file=pdf_file,
            port=8080,
            secret="test-secret",
            host="127.0.0.1",
            static_dir=static_dir
        )
        
        app = FastAPI()
        app.include_router(pdf_route.router)
        
        with patch("src.routes.pdf.get_settings", return_value=settings):
            client = TestClient(app)
            response = client.get("/get-pdf")
            
            # Empty file should still be served successfully
            assert response.status_code == 200
            assert response.content == b""
