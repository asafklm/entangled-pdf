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


class TestGetState:
    """Test suite for GET /state endpoint."""
    
    def test_get_state_returns_current_state(self, client):
        """Test that endpoint returns current PDF state with file path."""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "page": 5,
            "y": 150.5,
            "last_sync_time": 1234567890,
            "pdf_file": "/path/to/test.pdf",
            "pdf_loaded": True
        }
        
        with patch("src.routes.state.pdf_state", mock_state):
            response = client.get("/state")
            
            assert response.status_code == 200
            data = response.json()
            assert data["pdf_file"] == "/path/to/test.pdf"
            assert data["pdf_loaded"] is True
            assert data["page"] == 5
            assert data["y"] == 150.5
            assert data["last_sync_time"] == 1234567890
    
    def test_get_state_json_format(self, client):
        """Test that response is valid JSON with correct structure."""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "page": 1,
            "y": None,
            "last_sync_time": 1234567890,
            "pdf_file": None,
            "pdf_loaded": False
        }
        
        with patch("src.routes.state.pdf_state", mock_state):
            response = client.get("/state")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
            
            data = response.json()
            assert isinstance(data, dict)
            assert "pdf_file" in data
            assert "pdf_loaded" in data
            assert "page" in data
            assert "y" in data
            assert "last_sync_time" in data
    
    def test_get_state_default_values(self, client):
        """Test that endpoint returns default state values."""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "page": 1,
            "y": None,
            "last_sync_time": 1234567890,
            "pdf_file": None,
            "pdf_loaded": False
        }
        
        with patch("src.routes.state.pdf_state", mock_state):
            response = client.get("/state")
            
            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 1
            assert data["y"] is None
            assert data["pdf_loaded"] is False
    
    def test_get_state_reflects_updates(self, client):
        """Test that endpoint reflects state updates."""
        # First update
        mock_state1 = MagicMock()
        mock_state1.to_dict.return_value = {
            "page": 3,
            "y": 100.0,
            "last_sync_time": 1234567890,
            "pdf_file": "/path/to/doc1.pdf",
            "pdf_loaded": True
        }
        
        with patch("src.routes.state.pdf_state", mock_state1):
            response = client.get("/state")
            data = response.json()
            assert data["page"] == 3
            assert data["y"] == 100.0
            assert data["pdf_file"] == "/path/to/doc1.pdf"
        
        # Second update
        mock_state2 = MagicMock()
        mock_state2.to_dict.return_value = {
            "page": 7,
            "y": 250.5,
            "last_sync_time": 1234567891,
            "pdf_file": "/path/to/doc2.pdf",
            "pdf_loaded": True
        }
        
        with patch("src.routes.state.pdf_state", mock_state2):
            response = client.get("/state")
            data = response.json()
            assert data["page"] == 7
            assert data["y"] == 250.5
            assert data["pdf_file"] == "/path/to/doc2.pdf"
    
    def test_get_state_with_zero_y(self, client):
        """Test that y=0 is properly returned (not treated as None)."""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "page": 2,
            "y": 0.0,
            "last_sync_time": 1234567890,
            "pdf_file": "/path/to/test.pdf",
            "pdf_loaded": True
        }
        
        with patch("src.routes.state.pdf_state", mock_state):
            response = client.get("/state")
            
            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2
            assert data["y"] == 0.0
    
    def test_get_state_large_page_number(self, client):
        """Test with large page numbers."""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "page": 9999,
            "y": 5000.5,
            "last_sync_time": 1234567890,
            "pdf_file": "/path/to/big.pdf",
            "pdf_loaded": True
        }
        
        with patch("src.routes.state.pdf_state", mock_state):
            response = client.get("/state")
            
            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 9999
            assert data["y"] == 5000.5
    
    def test_get_state_timestamp_type(self, client):
        """Test that timestamp is returned as integer."""
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "page": 1,
            "y": None,
            "last_sync_time": 1234567890123,
            "pdf_file": None,
            "pdf_loaded": False
        }
        
        with patch("src.routes.state.pdf_state", mock_state):
            response = client.get("/state")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data["last_sync_time"], int)
            assert data["last_sync_time"] == 1234567890123
