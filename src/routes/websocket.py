"""WebSocket endpoint for real-time PDF synchronization.

Handles client connections and listens for incoming messages.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.connection_manager import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle WebSocket connections for real-time sync.
    
    Accepts connections and keeps them alive until the client disconnects.
    Messages are broadcast from the webhook endpoint, not received here.
    
    Args:
        websocket: The WebSocket connection
    """
    await manager.connect(websocket)
    try:
        # Keep connection alive, listening for messages
        # (we don't expect messages from clients, just the connection)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
