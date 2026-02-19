"""State endpoint for retrieving current PDF position.

Used by clients when they refocus to check for updates.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.state import pdf_state

router = APIRouter()


@router.get("/current-state")
async def get_state() -> JSONResponse:
    """Get the current PDF viewing state.
    
    Returns the current page, y-coordinate, and last update timestamp.
    Used by clients when they refocus to check for new updates.
    
    Returns:
        JSONResponse: Current state with page, y, and last_update_time
    """
    return JSONResponse(content=pdf_state.to_dict())
