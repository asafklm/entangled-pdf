"""State endpoint for retrieving current PDF position.

Used by clients when they refocus to check for updates.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.state import pdf_state

router = APIRouter()


@router.get("/state")
async def get_state(request: Request) -> JSONResponse:
    """Get the current PDF state including file path and viewing position.
    
    Returns the PDF file path, current page, y-coordinate, and last update timestamp.
    Used by clients when they refocus to check for new updates.
    
    When accessed from localhost (127.0.0.1 or ::1), includes the WebSocket
    authentication token for use by local management tools.
    
    Returns:
        JSONResponse: Current state with pdf_file, pdf_loaded, page, y, 
                     last_update_time, and optionally websocket_token
    """
    state_dict = pdf_state.to_dict()
    
    # Include token when accessed from localhost for management tools
    client_host = request.client.host if request.client else None
    if client_host in ("127.0.0.1", "::1", "localhost"):
        state_dict["websocket_token"] = pdf_state.websocket_token
    
    return JSONResponse(content=state_dict)
