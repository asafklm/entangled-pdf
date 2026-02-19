"""Tests for webhook endpoint."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from src.routes import webhook
from src.config import Settings


@pytest.fixture
def mock_settings(tmp_path):
    """Create mock settings for testing."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_text("dummy pdf content")
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    
    return Settings(
        pdf_file=pdf_file,
        port=8080,
        secret="test-secret-123",
        host="127.0.0.1",
        static_dir=static_dir
    )


@pytest.fixture
def client(mock_settings):
    """Create test client with mocked settings."""
    app = FastAPI()
    app.include_router(webhook.router)
    
    with patch("src.routes.webhook.get_settings", return_value=mock_settings):
        with patch("src.config.settings", mock_settings):
            yield TestClient(app)


class TestWebhookAuthentication:
    """Test suite for webhook authentication."""
    
    def test_webhook_success_valid_api_key(self, client):
        """Test successful webhook with valid API key."""
        with patch("src.routes.webhook.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            mock_manager.broadcast.return_value = None
            
            with patch("src.routes.webhook.pdf_state") as mock_state:
                mock_state.update = MagicMock()
                mock_state.last_update_time = 1234567890
                
                response = client.post(
                    "/webhook/update",
                    json={"page": 5, "y": 100.5},
                    headers={"X-API-Key": "test-secret-123"}
                )
                
                assert response.status_code == 200
                assert response.json()["status"] == "success"
                assert response.json()["page"] == 5
                assert response.json()["y"] == 100.5
                mock_manager.broadcast.assert_called_once()
    
    def test_webhook_unauthorized_invalid_api_key(self, client):
        """Test webhook with invalid API key returns 403."""
        response = client.post(
            "/webhook/update",
            json={"page": 5},
            headers={"X-API-Key": "wrong-secret"}
        )
        
        assert response.status_code == 403
        assert "Unauthorized" in response.json()["detail"]
    
    def test_webhook_unauthorized_missing_api_key(self, client):
        """Test webhook without API key returns 403."""
        response = client.post(
            "/webhook/update",
            json={"page": 5}
        )
        
        assert response.status_code == 403
        assert "Unauthorized" in response.json()["detail"]


class TestWebhookValidation:
    """Test suite for webhook input validation."""
    
    def test_webhook_invalid_page_number_string(self, client):
        """Test webhook with non-numeric page returns 400."""
        response = client.post(
            "/webhook/update",
            json={"page": "not-a-number"},
            headers={"X-API-Key": "test-secret-123"}
        )
        
        assert response.status_code == 400
        assert "Invalid page number" in response.json()["detail"]
    
    def test_webhook_invalid_page_number_none(self, client):
        """Test webhook with null page returns 400."""
        response = client.post(
            "/webhook/update",
            json={"page": None},
            headers={"X-API-Key": "test-secret-123"}
        )
        
        # None cannot be converted to int, so this should fail
        assert response.status_code == 400
        assert "Invalid page number" in response.json()["detail"]
    
    def test_webhook_missing_page_uses_default(self, client):
        """Test webhook without page defaults to 1."""
        with patch("src.routes.webhook.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            mock_manager.broadcast.return_value = None
            
            with patch("src.routes.webhook.pdf_state") as mock_state:
                mock_state.update = MagicMock()
                mock_state.last_update_time = 1234567890
                
                response = client.post(
                    "/webhook/update",
                    json={},
                    headers={"X-API-Key": "test-secret-123"}
                )
                
                assert response.status_code == 200
                assert response.json()["page"] == 1


class TestWebhookBroadcasting:
    """Test suite for webhook broadcasting functionality."""
    
    def test_webhook_broadcasts_to_clients(self, client):
        """Test that webhook broadcasts message to connected clients."""
        with patch("src.routes.webhook.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            mock_manager.broadcast.return_value = None
            
            with patch("src.routes.webhook.pdf_state") as mock_state:
                mock_state.update = MagicMock()
                mock_state.last_update_time = 1234567890
                
                response = client.post(
                    "/webhook/update",
                    json={"page": 3, "y": 150.0, "x": 50.0},
                    headers={"X-API-Key": "test-secret-123"}
                )
                
                assert response.status_code == 200
                mock_manager.broadcast.assert_called_once()
                
                # Verify broadcast message structure
                call_args = mock_manager.broadcast.call_args[0][0]
                assert call_args["action"] == "synctex"
                assert call_args["page"] == 3
                assert call_args["y"] == 150.0
                assert call_args["x"] == 50.0
                assert "timestamp" in call_args
    
    def test_webhook_updates_global_state(self, client):
        """Test that webhook updates the global PDF state."""
        with patch("src.routes.webhook.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            mock_manager.broadcast.return_value = None
            
            with patch("src.routes.webhook.pdf_state") as mock_state:
                mock_state.update = MagicMock()
                mock_state.last_update_time = 1234567890
                
                response = client.post(
                    "/webhook/update",
                    json={"page": 7, "y": 200.5},
                    headers={"X-API-Key": "test-secret-123"}
                )
                
                assert response.status_code == 200
                mock_state.update.assert_called_once_with(7, 200.5)
    
    def test_webhook_optional_coordinates(self, client):
        """Test webhook with only page number (no coordinates)."""
        with patch("src.routes.webhook.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            mock_manager.broadcast.return_value = None
            
            with patch("src.routes.webhook.pdf_state") as mock_state:
                mock_state.update = MagicMock()
                mock_state.last_update_time = 1234567890
                
                response = client.post(
                    "/webhook/update",
                    json={"page": 2},
                    headers={"X-API-Key": "test-secret-123"}
                )
                
                assert response.status_code == 200
                assert response.json()["page"] == 2
                assert response.json()["y"] is None
                assert response.json()["x"] is None
                
                # Verify broadcast includes null coordinates
                call_args = mock_manager.broadcast.call_args[0][0]
                assert call_args["y"] is None
                assert call_args["x"] is None
    
    def test_webhook_response_format(self, client):
        """Test webhook response format."""
        with patch("src.routes.webhook.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            mock_manager.broadcast.return_value = None
            
            with patch("src.routes.webhook.pdf_state") as mock_state:
                mock_state.update = MagicMock()
                mock_state.last_update_time = 1234567890
                
                response = client.post(
                    "/webhook/update",
                    json={"page": 10, "y": 300.0, "x": 100.0},
                    headers={"X-API-Key": "test-secret-123"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "status" in data
                assert "page" in data
                assert "x" in data
                assert "y" in data
                assert data["status"] == "success"
