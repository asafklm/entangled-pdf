"""Webhook endpoint for receiving PDF position updates.

Receives SyncTeX forward search coordinates and broadcasts them
to all connected WebSocket clients.
"""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.connection_manager import manager
from src.state import pdf_state

router = APIRouter()


@router.post("/webhook/update")
async def receive_webhook(
    data: dict,
    x_api_key: Optional[str] = Header(None)
) -> JSONResponse:
    """Receive PDF position updates and broadcast to clients.
    
    Authenticates requests using the X-API-Key header, updates the
    global state, and broadcasts the new position to all connected
    WebSocket clients.
    
    Args:
        data: JSON payload with page number and optional coordinates
            - page (int): Page number to navigate to (required)
            - y (float): Vertical position in PDF points (optional)
            - x (float): Horizontal position (optional, reserved)
        x_api_key: API key from X-API-Key header
    
    Returns:
        JSONResponse: Success status with the received parameters
    
    Raises:
        HTTPException: 403 if API key is invalid
        HTTPException: 400 if page number is missing or invalid
    """
    settings = get_settings()
    
    # Validate API key
    if x_api_key != settings.secret:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Extract and validate parameters
    try:
        page = int(data.get("page", 1))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid page number")
    
    x = data.get("x")  # Optional: PDF x coordinate from synctex
    y = data.get("y")  # Optional: PDF y coordinate from synctex
    
    # Update global state
    pdf_state.update(page, y)
    
    # Broadcast to all connected clients
    await manager.broadcast({
        "action": "synctex",
        "page": page,
        "x": x,
        "y": y,
        "timestamp": pdf_state.last_update_time
    })
    
    return JSONResponse(content={
        "status": "success",
        "page": page,
        "x": x,
        "y": y
    })
