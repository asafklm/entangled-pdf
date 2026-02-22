"""Integration tests for Webhook → State → Broadcast flow.

Tests the complete data flow from receiving a webhook to broadcasting
to connected WebSocket clients.
"""

import asyncio
import json
import time
from unittest.mock import patch

import pytest
import pytest_asyncio

from src.config import get_settings
from tests.integration.helpers import MockWebSocket


class TestWebhookBroadcastFlow:
    """Test the complete webhook → state → broadcast flow."""
    
    @pytest.mark.asyncio
    async def test_webhook_updates_state_and_broadcasts(
        self, test_client, reset_state, reset_connections
    ):
        """Test that webhook updates state and broadcasts to WebSocket clients."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        # Create mock WebSocket client
        mock_ws = MockWebSocket()
        
        # Connect the mock client
        await manager.connect(mock_ws)
        
        # Send webhook
        response = test_client.post(
            "/webhook/update",
            json={"page": 5, "y": 150.5},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # Verify state was updated
        assert pdf_state.current_page == 5
        assert pdf_state.current_y == 150.5
        
        # Verify broadcast was sent
        assert len(mock_ws.sent_messages) == 1
        broadcast = mock_ws.sent_messages[0]
        assert broadcast["action"] == "synctex"
        assert broadcast["page"] == 5
        assert broadcast["y"] == 150.5
        assert "timestamp" in broadcast
        
        # Cleanup
        manager.disconnect(mock_ws)
    
    @pytest.mark.asyncio
    async def test_multiple_webhooks_sequential_updates(
        self, test_client, reset_state, reset_connections
    ):
        """Test multiple sequential webhook updates."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        mock_ws = MockWebSocket()
        
        await manager.connect(mock_ws)
        
        # Send multiple webhooks
        updates = [
            {"page": 1, "y": 100},
            {"page": 2, "y": 200},
            {"page": 3, "y": 300},
        ]
        
        for update in updates:
            response = test_client.post(
                "/webhook/update",
                json=update,
                headers={"X-API-Key": get_settings().secret}
            )
            assert response.status_code == 200
            await asyncio.sleep(0.01)  # Small delay between updates
        
        # Verify final state
        assert pdf_state.current_page == 3
        assert pdf_state.current_y == 300
        
        # Verify all broadcasts were sent
        assert len(mock_ws.sent_messages) == 3
        
        # Cleanup
        manager.disconnect(mock_ws)
    
    @pytest.mark.asyncio
    async def test_webhook_broadcast_reaches_multiple_clients(
        self, test_client, reset_state, reset_connections
    ):
        """Test that one webhook reaches multiple WebSocket clients."""
        from src.connection_manager import manager
        
        # Create multiple mock clients
        clients = []
        for i in range(5):
            client = MockWebSocket()
            await manager.connect(client)
            clients.append(client)
        
        # Send single webhook
        response = test_client.post(
            "/webhook/update",
            json={"page": 10, "y": 500},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # Verify all clients received the broadcast
        for client in clients:
            assert len(client.sent_messages) == 1
            assert client.sent_messages[0]["page"] == 10
            assert client.sent_messages[0]["y"] == 500
        
        # Cleanup
        for client in clients:
            manager.disconnect(client)
    
    @pytest.mark.asyncio
    async def test_webhook_with_y_coordinate_full_flow(
        self, test_client, reset_state, reset_connections
    ):
        """Test complete flow with y-coordinate (page + scroll position)."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        mock_ws = MockWebSocket()
        
        await manager.connect(mock_ws)
        
        # Send webhook with y-coordinate
        response = test_client.post(
            "/webhook/update",
            json={"page": 7, "y": 250.75, "x": 50},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # Verify state
        assert pdf_state.current_page == 7
        assert pdf_state.current_y == 250.75
        
        # Verify broadcast includes all fields
        assert len(mock_ws.sent_messages) == 1
        broadcast = mock_ws.sent_messages[0]
        assert broadcast["page"] == 7
        assert broadcast["y"] == 250.75
        assert broadcast["x"] == 50  # x should be included too
        
        # Cleanup
        manager.disconnect(mock_ws)
    
    @pytest.mark.asyncio
    async def test_webhook_without_y_coordinate_full_flow(
        self, test_client, reset_state, reset_connections
    ):
        """Test complete flow with page only (no scroll position)."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        mock_ws = MockWebSocket()
        
        await manager.connect(mock_ws)
        
        # Send webhook without y-coordinate
        response = test_client.post(
            "/webhook/update",
            json={"page": 2},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # Verify state
        assert pdf_state.current_page == 2
        assert pdf_state.current_y is None
        
        # Verify broadcast
        assert len(mock_ws.sent_messages) == 1
        broadcast = mock_ws.sent_messages[0]
        assert broadcast["page"] == 2
        assert broadcast["y"] is None
        
        # Cleanup
        manager.disconnect(mock_ws)
