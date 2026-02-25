"""State endpoint for retrieving current PDF position.

Used by clients when they refocus to check for updates.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.config import get_settings
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


@router.get("/current-pdf")
async def get_current_pdf() -> JSONResponse:
    """Get the path of the PDF file currently being served.
    
    Used by VimTeX to check if the server is running and which
    PDF file it's serving. This helps determine whether to start
    a new server or reuse the existing one.
    
    Returns:
        JSONResponse: Object containing the current PDF file path
    """
    settings = get_settings()
    return JSONResponse(content={"pdf_file": str(settings.pdf_file)})
