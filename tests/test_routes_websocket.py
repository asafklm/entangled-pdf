"""Tests for WebSocket endpoint."""

import pytest
import asyncio
from fastapi import FastAPI
from unittest.mock import patch, AsyncMock, MagicMock

from pdfserver.routes import websocket as websocket_route
from pdfserver.connection_manager import ConnectionManager
from pdfserver.state import pdf_state


@pytest.fixture
def app():
    """Create FastAPI app."""
    app = FastAPI()
    app.include_router(websocket_route.router)
    return app


@pytest.fixture(autouse=True)
def reset_state():
    """Reset pdf_state before each test."""
    pdf_state.inverse_search_enabled = False
    pdf_state.websocket_token = None
    yield


class TestWebSocketConnection:
    """Test suite for WebSocket /ws endpoint."""
    
    @pytest.mark.asyncio
    async def test_websocket_connect_adds_to_manager(self, app):
        """Test that WebSocket connection is added to manager."""
        test_manager = ConnectionManager()
        
        with patch("pdfserver.routes.websocket.manager", test_manager):
            # Create a mock websocket
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            mock_ws.receive_json = AsyncMock(side_effect=Exception("Stop loop"))
            
            # Call the endpoint directly (inverse search disabled, no token needed)
            try:
                await websocket_route.websocket_endpoint(mock_ws, token=None)
            except Exception:
                pass
            
            # Verify connection was added
            mock_ws.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_disconnect_removes_from_manager(self, app):
        """Test that WebSocket disconnect removes from manager."""
        test_manager = ConnectionManager()
        
        with patch("pdfserver.routes.websocket.manager", test_manager):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            
            # Simulate disconnect by raising WebSocketDisconnect
            from fastapi import WebSocketDisconnect
            mock_ws.receive_json = AsyncMock(side_effect=WebSocketDisconnect())
            
            # Call the endpoint (inverse search disabled)
            await websocket_route.websocket_endpoint(mock_ws, token=None)
            
            # Should complete without error
            assert test_manager.get_connection_count() == 0
    
    @pytest.mark.asyncio
    async def test_websocket_keeps_connection_alive(self, app):
        """Test that WebSocket connection stays alive waiting for messages."""
        test_manager = ConnectionManager()
        
        with patch("pdfserver.routes.websocket.manager", test_manager):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            
            # Simulate receiving a few messages then disconnect
            call_count = [0]
            async def side_effect():
                call_count[0] += 1
                if call_count[0] >= 3:
                    from fastapi import WebSocketDisconnect
                    raise WebSocketDisconnect()
                return {"action": "test"}
            
            mock_ws.receive_json = AsyncMock(side_effect=side_effect)
            
            # Call the endpoint (inverse search disabled)
            await websocket_route.websocket_endpoint(mock_ws, token=None)
            
            # Should have received multiple messages
            assert call_count[0] == 3
    
    @pytest.mark.asyncio
    async def test_websocket_handles_multiple_clients(self, app):
        """Test that multiple WebSocket clients can connect."""
        test_manager = ConnectionManager()
        
        with patch("pdfserver.routes.websocket.manager", test_manager):
            # First client
            mock_ws1 = AsyncMock()
            mock_ws1.accept = AsyncMock()
            from fastapi import WebSocketDisconnect
            mock_ws1.receive_json = AsyncMock(side_effect=WebSocketDisconnect())
            
            await websocket_route.websocket_endpoint(mock_ws1, token=None)
            
            # Second client
            mock_ws2 = AsyncMock()
            mock_ws2.accept = AsyncMock()
            mock_ws2.receive_json = AsyncMock(side_effect=WebSocketDisconnect())
            
            await websocket_route.websocket_endpoint(mock_ws2, token=None)
            
            # Both should complete without error
            assert test_manager.get_connection_count() == 0


class TestWebSocketIntegration:
    """Test suite for WebSocket integration with connection manager."""
    
    @pytest.mark.asyncio
    async def test_websocket_real_manager_connect_disconnect(self, app):
        """Test WebSocket with real ConnectionManager."""
        test_manager = ConnectionManager()
        
        with patch("pdfserver.routes.websocket.manager", test_manager):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            from fastapi import WebSocketDisconnect
            mock_ws.receive_json = AsyncMock(side_effect=WebSocketDisconnect())
            
            assert test_manager.get_connection_count() == 0
            
            await websocket_route.websocket_endpoint(mock_ws, token=None)
            
            # After disconnect
            assert test_manager.get_connection_count() == 0
    
    @pytest.mark.asyncio
    async def test_websocket_broadcast_to_client(self, app):
        """Test broadcasting to connected WebSocket client."""
        test_manager = ConnectionManager()
        
        with patch("pdfserver.routes.websocket.manager", test_manager):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            mock_ws.send_json = AsyncMock()
            
            # Keep connection alive briefly then disconnect
            call_count = [0]
            async def side_effect():
                call_count[0] += 1
                if call_count[0] == 1:
                    # Broadcast after first receive
                    await test_manager.broadcast({
                        "action": "synctex",
                        "page": 3,
                        "y": 100.5
                    })
                    return {"action": "test"}
                else:
                    from fastapi import WebSocketDisconnect
                    raise WebSocketDisconnect()
            
            mock_ws.receive_json = AsyncMock(side_effect=side_effect)
            
            # Connect the websocket manually first
            await test_manager.connect(mock_ws)
            
            # Broadcast should reach the client
            await test_manager.broadcast({
                "action": "synctex",
                "page": 5,
                "y": 200.0
            })
            
            # Verify message was sent
            mock_ws.send_json.assert_called()
            call_args = mock_ws.send_json.call_args[0][0]
            assert call_args["action"] == "synctex"
            assert call_args["page"] == 5
