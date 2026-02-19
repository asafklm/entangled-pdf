"""WebSocket connection management for PdfServer.

Provides a ConnectionManager class to handle WebSocket connections,
broadcasting messages, and connection lifecycle management.
"""

import logging
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect

# Configure logging
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time PDF synchronization.
    
    This class handles client connections, disconnections, and broadcasting
    messages to all connected clients. It's designed as a singleton to maintain
    a single set of active connections across the application.
    
    Attributes:
        active_connections: Set of currently connected WebSocket clients
    
    Example:
        >>> manager = ConnectionManager()
        >>> await manager.connect(websocket)
        >>> await manager.broadcast({"action": "sync", "page": 1})
    """
    
    def __init__(self) -> None:
        """Initialize the connection manager with an empty connection set."""
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to accept
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.debug(f"New WebSocket connection. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to remove
        
        Note:
            Silently ignores if the websocket is not in the active set
            (e.g., if it was already removed or never connected).
        """
        try:
            self.active_connections.remove(websocket)
            logger.debug(f"WebSocket disconnected. Total: {len(self.active_connections)}")
        except KeyError:
            # Connection was already removed or never added
            pass
    
    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients.
        
        Args:
            message: Dictionary to send as JSON to all clients
        
        Note:
            Failed sends are logged but don't stop broadcasting to other clients.
            This ensures one bad connection doesn't affect others.
        """
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                # Mark for removal but continue broadcasting
                disconnected.add(connection)
                logger.warning(f"Failed to send to WebSocket: {e}")
        
        # Clean up any failed connections
        for conn in disconnected:
            self.disconnect(conn)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections.
        
        Returns:
            int: Number of currently connected clients
        """
        return len(self.active_connections)


# Singleton instance used across the application
manager = ConnectionManager()
