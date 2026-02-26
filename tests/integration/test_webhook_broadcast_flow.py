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
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test that webhook updates state and broadcasts to WebSocket clients."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        # Create mock WebSocket client
        mock_ws = MockWebSocket()
        
        # Connect the mock client
        await manager.connect(mock_ws)
        
        # Send webhook with synctex parameters (line: 50, col: 5 -> page: 5, y: 505)
        response = test_client.post(
            "/webhook/update",
            json={"line": 50, "col": 5, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # Verify state was updated (line 50 -> page 5, y 505)
        assert pdf_state.current_page == 5
        assert pdf_state.current_y == 505.0
        
        # Verify broadcast was sent
        assert len(mock_ws.sent_messages) == 1
        broadcast = mock_ws.sent_messages[0]
        assert broadcast["action"] == "synctex"
        assert broadcast["page"] == 5
        assert broadcast["y"] == 505.0
        assert "timestamp" in broadcast
        
        # Cleanup
        manager.disconnect(mock_ws)
    
    @pytest.mark.asyncio
    async def test_multiple_webhooks_sequential_updates(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test multiple sequential webhook updates."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        mock_ws = MockWebSocket()
        
        await manager.connect(mock_ws)
        
        # Send multiple webhooks with synctex parameters
        updates = [
            {"line": 10, "col": 0},    # -> page 1, y 100
            {"line": 20, "col": 0},    # -> page 2, y 200
            {"line": 30, "col": 0},    # -> page 3, y 300
        ]
        
        for update in updates:
            response = test_client.post(
                "/webhook/update",
                json={**update, "tex_file": "test.tex", "pdf_file": "test.pdf"},
                headers={"X-API-Key": get_settings().secret}
            )
            assert response.status_code == 200
            await asyncio.sleep(0.01)  # Small delay between updates
        
        # Verify final state (last update: line 30 -> page 3, y 300)
        assert pdf_state.current_page == 3
        assert pdf_state.current_y == 300.0
        
        # Verify all broadcasts were sent
        assert len(mock_ws.sent_messages) == 3
        
        # Cleanup
        manager.disconnect(mock_ws)
    
    @pytest.mark.asyncio
    async def test_webhook_broadcast_reaches_multiple_clients(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test that one webhook reaches multiple WebSocket clients."""
        from src.connection_manager import manager
        
        # Create multiple mock clients
        clients = []
        for i in range(5):
            client = MockWebSocket()
            await manager.connect(client)
            clients.append(client)
        
        # Send single webhook with synctex params (line: 100, col: 0 -> page 10, y 1000)
        response = test_client.post(
            "/webhook/update",
            json={"line": 100, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # Verify all clients received the broadcast
        for client in clients:
            assert len(client.sent_messages) == 1
            assert client.sent_messages[0]["page"] == 10
            assert client.sent_messages[0]["y"] == 1000.0
        
        # Cleanup
        for client in clients:
            manager.disconnect(client)
    
    @pytest.mark.asyncio
    async def test_webhook_with_y_coordinate_full_flow(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test complete flow with y-coordinate (page + scroll position)."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        mock_ws = MockWebSocket()
        
        await manager.connect(mock_ws)
        
        # Send webhook with synctex params (line: 70, col: 25 -> page 7, y 725, x 125)
        response = test_client.post(
            "/webhook/update",
            json={"line": 70, "col": 25, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # Verify state (line 70 -> page 7, y 725)
        assert pdf_state.current_page == 7
        assert pdf_state.current_y == 725.0
        
        # Verify broadcast includes all fields
        assert len(mock_ws.sent_messages) == 1
        broadcast = mock_ws.sent_messages[0]
        assert broadcast["page"] == 7
        assert broadcast["y"] == 725.0
        assert broadcast["x"] == 125.0  # x from col * 5
        
        # Cleanup
        manager.disconnect(mock_ws)
    
    @pytest.mark.asyncio
    async def test_webhook_without_y_coordinate_full_flow(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test complete flow with page only (no scroll position)."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        mock_ws = MockWebSocket()
        
        await manager.connect(mock_ws)
        
        # Send webhook with synctex params (line: 20, col: 0 -> page 2, y 200)
        response = test_client.post(
            "/webhook/update",
            json={"line": 20, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # Verify state (line 20 -> page 2, y 200)
        assert pdf_state.current_page == 2
        assert pdf_state.current_y == 200.0
        
        # Verify broadcast
        assert len(mock_ws.sent_messages) == 1
        broadcast = mock_ws.sent_messages[0]
        assert broadcast["page"] == 2
        assert broadcast["y"] == 200.0
        
        # Cleanup
        manager.disconnect(mock_ws)
