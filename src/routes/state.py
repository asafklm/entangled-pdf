"""State endpoint for retrieving current PDF position.

Used by clients when they refocus to check for updates.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.state import pdf_state

router = APIRouter()


@router.get("/state")
async def get_state() -> JSONResponse:
    """Get the current PDF state including file path and viewing position.
    
    Returns the PDF file path, current page, y-coordinate, and last update timestamp.
    Used by clients when they refocus to check for new updates.
    
    Returns:
        JSONResponse: Current state with pdf_file, page, y, and last_update_time
    """
    settings = get_settings()
    state_dict = pdf_state.to_dict()
    state_dict["pdf_file"] = str(settings.pdf_file)
    return JSONResponse(content=state_dict)
