"""Tests for state endpoint."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.routes import state as state_route


@pytest.fixture
def client():
    """Create test client for state endpoint."""
    app = FastAPI()
    app.include_router(state_route.router)
    return TestClient(app)


@pytest.fixture
def mock_settings(tmp_path):
    """Create mock settings for testing."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_text("dummy pdf content")
    
    mock_settings = MagicMock()
    mock_settings.pdf_file = pdf_file
    return mock_settings


class TestGetState:
    """Test suite for GET /state endpoint."""
    
    def test_get_state_returns_current_state(self, client, mock_settings):
        """Test that endpoint returns current PDF state with file path."""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "page": 5,
            "y": 150.5,
            "last_update_time": 1234567890
        }
        
        with patch("src.routes.state.pdf_state", mock_state):
            with patch("src.routes.state.get_settings", return_value=mock_settings):
                response = client.get("/state")
                
                assert response.status_code == 200
                data = response.json()
                assert data["pdf_file"] == str(mock_settings.pdf_file)
                assert data["page"] == 5
                assert data["y"] == 150.5
                assert data["last_update_time"] == 1234567890
    
    def test_get_state_json_format(self, client, mock_settings):
        """Test that response is valid JSON with correct structure."""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "page": 1,
            "y": None,
            "last_update_time": 1234567890
        }
        
        with patch("src.routes.state.pdf_state", mock_state):
            with patch("src.routes.state.get_settings", return_value=mock_settings):
                response = client.get("/state")
                
                assert response.status_code == 200
                assert response.headers["content-type"] == "application/json"
                
                data = response.json()
                assert isinstance(data, dict)
                assert "pdf_file" in data
                assert "page" in data
                assert "y" in data
                assert "last_update_time" in data
    
    def test_get_state_default_values(self, client, mock_settings):
        """Test that endpoint returns default state values."""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "page": 1,
            "y": None,
            "last_update_time": 1234567890
        }
        
        with patch("src.routes.state.pdf_state", mock_state):
            with patch("src.routes.state.get_settings", return_value=mock_settings):
                response = client.get("/state")
                
                assert response.status_code == 200
                data = response.json()
                assert data["page"] == 1
                assert data["y"] is None
    
    def test_get_state_reflects_updates(self, client, mock_settings):
        """Test that endpoint reflects state updates."""
        # First update
        mock_state1 = MagicMock()
        mock_state1.to_dict.return_value = {
            "page": 3,
            "y": 100.0,
            "last_update_time": 1234567890
        }
        
        with patch("src.routes.state.pdf_state", mock_state1):
            with patch("src.routes.state.get_settings", return_value=mock_settings):
                response = client.get("/state")
                data = response.json()
                assert data["page"] == 3
                assert data["y"] == 100.0
        
        # Second update
        mock_state2 = MagicMock()
        mock_state2.to_dict.return_value = {
            "page": 7,
            "y": 250.5,
            "last_update_time": 1234567891
        }
        
        with patch("src.routes.state.pdf_state", mock_state2):
            with patch("src.routes.state.get_settings", return_value=mock_settings):
                response = client.get("/state")
                data = response.json()
                assert data["page"] == 7
                assert data["y"] == 250.5
    
    def test_get_state_with_zero_y(self, client, mock_settings):
        """Test that y=0 is properly returned (not treated as None)."""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "page": 2,
            "y": 0.0,
            "last_update_time": 1234567890
        }
        
        with patch("src.routes.state.pdf_state", mock_state):
            with patch("src.routes.state.get_settings", return_value=mock_settings):
                response = client.get("/state")
                
                assert response.status_code == 200
                data = response.json()
                assert data["page"] == 2
                assert data["y"] == 0.0
    
    def test_get_state_large_page_number(self, client, mock_settings):
        """Test with large page numbers."""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "page": 9999,
            "y": 5000.5,
            "last_update_time": 1234567890
        }
        
        with patch("src.routes.state.pdf_state", mock_state):
            with patch("src.routes.state.get_settings", return_value=mock_settings):
                response = client.get("/state")
                
                assert response.status_code == 200
                data = response.json()
                assert data["page"] == 9999
                assert data["y"] == 5000.5
    
    def test_get_state_timestamp_type(self, client, mock_settings):
        """Test that timestamp is returned as integer."""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "page": 1,
            "y": None,
            "last_update_time": 1234567890123
        }
        
        with patch("src.routes.state.pdf_state", mock_state):
            with patch("src.routes.state.get_settings", return_value=mock_settings):
                response = client.get("/state")
                
                assert response.status_code == 200
                data = response.json()
                assert isinstance(data["last_update_time"], int)
                assert data["last_update_time"] == 1234567890123
