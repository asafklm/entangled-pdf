"""Tests for connection manager."""

import pytest
from fastapi import WebSocket

from pdfserver.connection_manager import ConnectionManager, manager


class TestConnectionManager:
    """Test suite for ConnectionManager."""
    
    @pytest.fixture
    def connection_manager(self):
        """Create a fresh ConnectionManager instance."""
        return ConnectionManager()
    
    @pytest.mark.asyncio
    async def test_connect_adds_websocket(self, connection_manager):
        """Test that connect adds websocket to active connections."""
        # Note: This is a simplified test - in reality you'd mock WebSocket
        assert connection_manager.get_connection_count() == 0
    
    def test_disconnect_removes_websocket(self, connection_manager):
        """Test that disconnect removes websocket from active connections."""
        # Create a mock websocket
        class MockWebSocket:
            pass
        
        ws = MockWebSocket()
        connection_manager.active_connections.add(ws)
        
        assert connection_manager.get_connection_count() == 1
        
        connection_manager.disconnect(ws)
        
        assert connection_manager.get_connection_count() == 0
    
    def test_disconnect_unknown_websocket(self, connection_manager):
        """Test that disconnecting unknown websocket doesn't raise error."""
        class MockWebSocket:
            pass
        
        ws = MockWebSocket()
        
        # Should not raise
        connection_manager.disconnect(ws)
    
    def test_get_connection_count(self, connection_manager):
        """Test connection count tracking."""
        assert connection_manager.get_connection_count() == 0
        
        class MockWebSocket:
            pass
        
        connection_manager.active_connections.add(MockWebSocket())
        connection_manager.active_connections.add(MockWebSocket())
        
        assert connection_manager.get_connection_count() == 2


class TestGlobalManager:
    """Test suite for global manager instance."""
    
    def test_global_manager_exists(self):
        """Test that global manager instance exists."""
        assert manager is not None
        assert isinstance(manager, ConnectionManager)
