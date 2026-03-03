"""Load PDF endpoint for dynamically loading PDF files.

Provides a minimal API endpoint to load or change the PDF file without restarting
the server. Broadcasts a reload message to all connected WebSocket clients.
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.connection_manager import manager
from src.state import pdf_state

router = APIRouter()


@router.post("/api/load-pdf")
async def load_pdf(
    data: dict,
    x_api_key: Optional[str] = Header(None)
) -> JSONResponse:
    """Load a new PDF file dynamically.
    
    Updates the server's current PDF file and broadcasts a reload
    to all connected WebSocket clients.
    
    Args:
        data: JSON payload with PDF path
            - pdf_path (str): Absolute or relative path to PDF file
        x_api_key: API key from X-API-Key header
    
    Returns:
        JSONResponse: Success status
    
    Raises:
        HTTPException: 403 if API key is invalid, 400 if PDF not found
    """
    settings = get_settings()
    
    # Validate API key
    if x_api_key != settings.secret:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Extract PDF path
    pdf_path_str = data.get("pdf_path")
    if not pdf_path_str:
        raise HTTPException(status_code=400, detail="Missing required field: pdf_path")
    
    # Resolve PDF path
    pdf_path = Path(pdf_path_str)
    if not pdf_path.is_absolute():
        pdf_path = pdf_path.resolve()
    
    # Validate PDF file exists
    if not pdf_path.exists():
        raise HTTPException(status_code=400, detail=f"PDF file not found: {pdf_path}")
    
    # Update the server's PDF file
    settings.pdf_file = pdf_path
    
    # Update pdf_state with new file and get mtime
    pdf_state.update_pdf(pdf_path)
    pdf_state.update(1, None)  # Reset to page 1
    
    # Broadcast reload to all connected clients
    await manager.broadcast({
        "action": "reload",
        "pdf_mtime": pdf_state.pdf_mtime
    })
    
    return JSONResponse(content={
        "status": "success",
        "pdf_file": str(pdf_path),
        "filename": pdf_path.name,
        "changed": True
    })
