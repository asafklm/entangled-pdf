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
    
    def test_webhook_success_valid_api_key(self, client, mock_settings):
        """Test successful webhook with valid API key and valid synctex result."""
        with patch("src.routes.webhook.run_synctex_view", new_callable=AsyncMock) as mock_synctex:
            mock_synctex.return_value = {
                "Page": "5",
                "y": "150.5",
                "x": "100.0"
            }
            
            with patch("src.routes.webhook.manager") as mock_manager:
                mock_manager.broadcast = AsyncMock()
                mock_manager.broadcast.return_value = None
                
                with patch("src.routes.webhook.pdf_state") as mock_state:
                    mock_state.update = MagicMock()
                    mock_state.last_update_time = 1234567890
                    
                    response = client.post(
                        "/webhook/update",
                        json={
                            "line": 42,
                            "col": 10,
                            "tex_file": "/path/to/file.tex",
                            "pdf_file": str(mock_settings.pdf_file)
                        },
                        headers={"X-API-Key": "test-secret-123"}
                    )
                    
                    assert response.status_code == 200
                    assert response.json()["status"] == "success"
                    assert response.json()["page"] == 5
                    assert response.json()["y"] == 150.5
                    assert response.json()["x"] == 100.0
                    mock_manager.broadcast.assert_called_once()
    
    def test_webhook_unauthorized_invalid_api_key(self, client):
        """Test webhook with invalid API key returns 403."""
        response = client.post(
            "/webhook/update",
            json={
                "line": 42,
                "col": 10,
                "tex_file": "/path/to/file.tex",
                "pdf_file": "/path/to/file.pdf"
            },
            headers={"X-API-Key": "wrong-secret"}
        )
        
        assert response.status_code == 403
        assert "Unauthorized" in response.json()["detail"]
    
    def test_webhook_unauthorized_missing_api_key(self, client):
        """Test webhook without API key returns 403."""
        response = client.post(
            "/webhook/update",
            json={
                "line": 42,
                "col": 10,
                "tex_file": "/path/to/file.tex",
                "pdf_file": "/path/to/file.pdf"
            }
        )
        
        assert response.status_code == 403
        assert "Unauthorized" in response.json()["detail"]


class TestWebhookSynctexFailure:
    """Test suite for webhook when synctex fails or no parameters provided."""
    
    def test_webhook_missing_synctex_params(self, client):
        """Test webhook without synctex parameters returns success with page=None."""
        response = client.post(
            "/webhook/update",
            json={},
            headers={"X-API-Key": "test-secret-123"}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["page"] is None
    
    def test_webhook_invalid_synctex_params(self, client):
        """Test webhook with invalid synctex parameters returns success with page=None."""
        response = client.post(
            "/webhook/update",
            json={
                "line": "invalid",
                "col": 10,
                "tex_file": "/path/to/file.tex",
                "pdf_file": "/path/to/file.pdf"
            },
            headers={"X-API-Key": "test-secret-123"}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["page"] is None
    
    def test_webhook_synctex_lookup_fails(self, client, mock_settings):
        """Test webhook when synctex lookup fails returns success with page=None."""
        with patch("src.routes.webhook.run_synctex_view", new_callable=AsyncMock) as mock_synctex:
            mock_synctex.return_value = None
            
            response = client.post(
                "/webhook/update",
                json={
                    "line": 42,
                    "col": 10,
                    "tex_file": "/path/to/file.tex",
                    "pdf_file": str(mock_settings.pdf_file)
                },
                headers={"X-API-Key": "test-secret-123"}
            )
            
            assert response.status_code == 200
            assert response.json()["status"] == "success"
            assert response.json()["page"] is None


class TestWebhookBroadcasting:
    """Test suite for webhook broadcasting functionality."""
    
    def test_webhook_broadcasts_synctex_result(self, client, mock_settings):
        """Test that webhook broadcasts synctex result to connected clients."""
        with patch("src.routes.webhook.run_synctex_view", new_callable=AsyncMock) as mock_synctex:
            mock_synctex.return_value = {
                "Page": "3",
                "y": "150.0",
                "x": "50.0"
            }
            
            with patch("src.routes.webhook.manager") as mock_manager:
                mock_manager.broadcast = AsyncMock()
                mock_manager.broadcast.return_value = None
                
                with patch("src.routes.webhook.pdf_state") as mock_state:
                    mock_state.update = MagicMock()
                    mock_state.last_update_time = 1234567890
                    
                    response = client.post(
                        "/webhook/update",
                        json={
                            "line": 10,
                            "col": 5,
                            "tex_file": "/path/to/file.tex",
                            "pdf_file": str(mock_settings.pdf_file)
                        },
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
    
    def test_webhook_updates_global_state(self, client, mock_settings):
        """Test that webhook updates the global PDF state."""
        with patch("src.routes.webhook.run_synctex_view", new_callable=AsyncMock) as mock_synctex:
            mock_synctex.return_value = {
                "Page": "7",
                "y": "200.5",
                "x": "100.0"
            }
            
            with patch("src.routes.webhook.manager") as mock_manager:
                mock_manager.broadcast = AsyncMock()
                mock_manager.broadcast.return_value = None
                
                with patch("src.routes.webhook.pdf_state") as mock_state:
                    mock_state.update = MagicMock()
                    mock_state.last_update_time = 1234567890
                    
                    response = client.post(
                        "/webhook/update",
                        json={
                            "line": 100,
                            "col": 20,
                            "tex_file": "/path/to/file.tex",
                            "pdf_file": str(mock_settings.pdf_file)
                        },
                        headers={"X-API-Key": "test-secret-123"}
                    )
                    
                    assert response.status_code == 200
                    mock_state.update.assert_called_once_with(7, 200.5)
    
    def test_webhook_no_scroll_when_synctex_fails(self, client, mock_settings):
        """Test that webhook returns success with page=None when synctex fails."""
        with patch("src.routes.webhook.run_synctex_view", new_callable=AsyncMock) as mock_synctex:
            mock_synctex.return_value = None  # synctex fails
            
            response = client.post(
                "/webhook/update",
                json={
                    "line": 42,
                    "col": 10,
                    "tex_file": "/path/to/file.tex",
                    "pdf_file": str(mock_settings.pdf_file)
                },
                headers={"X-API-Key": "test-secret-123"}
            )
            
            assert response.status_code == 200
            assert response.json()["status"] == "success"
            assert response.json()["page"] is None
