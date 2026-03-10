"""Integration tests for WebSocket connection lifecycle.

Tests connection handling with real WebSocket clients, including
reconnection, disconnection, and message delivery.
"""

import asyncio
import time
from unittest.mock import patch

import pytest
from src.config import get_settings
from tests.integration.helpers import MockWebSocket


class TestWebSocketLifecycle:
    """Test suite for WebSocket connection lifecycle."""
    
    @pytest.mark.asyncio
    async def test_client_receives_message_after_reconnect(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test that client receives message after reconnecting."""
        from src.connection_manager import manager
        
        # First client connects
        client1 = MockWebSocket()
        await manager.connect(client1)
        
        # Send first message (line: 30 -> page 3, y 300)
        response = test_client.post(
            "/webhook/update",
            json={"line": 30, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # Client receives first message
        assert len(client1.sent_messages) == 1
        assert client1.sent_messages[0]["page"] == 3
        
        # Client disconnects
        manager.disconnect(client1)
        client1.disconnect()
        
        # New client connects
        client2 = MockWebSocket()
        await manager.connect(client2)
        
        # Send second message (line: 50 -> page 5, y 500)
        response = test_client.post(
            "/webhook/update",
            json={"line": 50, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # New client receives second message only
        assert len(client2.sent_messages) == 1
        assert client2.sent_messages[0]["page"] == 5
        
        # Cleanup
        manager.disconnect(client2)
    
    @pytest.mark.asyncio
    async def test_broadcast_skips_disconnected_clients(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test that broadcast doesn't fail when some clients disconnect."""
        from src.connection_manager import manager
        
        # Create 3 clients
        clients = []
        for i in range(3):
            # Middle client will fail
            client = MockWebSocket(should_fail=(i == 1))
            await manager.connect(client)
            clients.append(client)
        
        # First client disconnects
        manager.disconnect(clients[0])
        clients[0].disconnect()
        
        # Send broadcast (should not crash despite failures) (line: 70 -> page 7, y 700)
        response = test_client.post(
            "/webhook/update",
            json={"line": 70, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # Third client should receive (first disconnected, second failed)
        assert len(clients[2].sent_messages) == 1
        assert clients[2].sent_messages[0]["page"] == 7
        
        # Verify connection count is correct
        assert manager.get_connection_count() == 1  # Only client 3 remains
        
        # Cleanup
        for client in clients:
            manager.disconnect(client)
    
    @pytest.mark.asyncio
    async def test_multiple_clients_receive_same_message(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test that 10+ simultaneous connections all receive broadcast."""
        from src.connection_manager import manager
        
        # Create 15 clients
        clients = []
        for i in range(15):
            client = MockWebSocket()
            await manager.connect(client)
            clients.append(client)
        
        # Send single broadcast (line: 100 -> page 10, y 1000)
        response = test_client.post(
            "/webhook/update",
            json={"line": 100, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # All 15 clients should receive the same message
        for client in clients:
            assert len(client.sent_messages) == 1
            assert client.sent_messages[0]["page"] == 10
            assert client.sent_messages[0]["y"] == 1000.0
        
        # Cleanup
        for client in clients:
            manager.disconnect(client)
    
    @pytest.mark.asyncio
    async def test_websocket_message_format_integrity(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Verify JSON structure matches expected format."""
        from src.connection_manager import manager
        from src.state import pdf_state
        
        client = MockWebSocket()
        await manager.connect(client)
        
        # Send webhook with synctex params (line: 30, col: 5 -> page 3, y 305, x 25)
        response = test_client.post(
            "/webhook/update",
            json={"line": 30, "col": 5, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # Verify message structure
        assert len(client.sent_messages) == 1
        msg = client.sent_messages[0]
        
        # Required fields
        assert "action" in msg
        assert "page" in msg
        assert "y" in msg
        assert "x" in msg
        assert "timestamp" in msg
        
        # Types
        assert isinstance(msg["action"], str)
        assert isinstance(msg["page"], int)
        assert isinstance(msg["y"], float)
        assert isinstance(msg["x"], float)
        assert isinstance(msg["timestamp"], int)
        
        # Values (line 30, col 5 -> page 3, y 305, x 25)
        assert msg["action"] == "synctex"
        assert msg["page"] == 3
        assert msg["y"] == 305.0
        assert msg["x"] == 25.0
        assert msg["timestamp"] == pdf_state.last_sync_time
        
        # Cleanup
        manager.disconnect(client)
    
    @pytest.mark.asyncio
    async def test_websocket_connection_accepted(
        self, test_client, reset_connections
    ):
        """Test that WebSocket connections are properly accepted."""
        from src.connection_manager import manager
        
        client = MockWebSocket()
        
        assert not client.accepted
        
        await manager.connect(client)
        
        assert client.accepted
        assert manager.get_connection_count() == 1
        
        # Cleanup
        manager.disconnect(client)
    
    @pytest.mark.asyncio
    async def test_multiple_broadcasts_sequence_integrity(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test that multiple broadcasts maintain sequence."""
        from src.connection_manager import manager
        
        client = MockWebSocket()
        await manager.connect(client)
        
        # Send 5 sequential broadcasts using synctex params
        # Lines 10, 20, 30, 40, 50 -> pages 1, 2, 3, 4, 5
        for i in range(5):
            line = (i + 1) * 10  # 10, 20, 30, 40, 50
            response = test_client.post(
                "/webhook/update",
                json={"line": line, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
                headers={"X-API-Key": get_settings().secret}
            )
            assert response.status_code == 200
        
        # Verify all 5 received in order
        assert len(client.sent_messages) == 5
        
        for i, msg in enumerate(client.sent_messages):
            expected_page = i + 1  # 1, 2, 3, 4, 5
            expected_y = (i + 1) * 10 * 10  # 100, 200, 300, 400, 500
            assert msg["page"] == expected_page
            assert msg["y"] == float(expected_y)
        
        # Cleanup
        manager.disconnect(client)
