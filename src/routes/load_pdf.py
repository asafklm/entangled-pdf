"""Load PDF endpoint for dynamically loading PDF files.

Provides a minimal API endpoint to load or change the PDF file without restarting
the server. Broadcasts a reload message to all connected WebSocket clients.
Supports configuring inverse search command for LaTeX editing workflows.
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.connection_manager import manager
from src.state import generate_websocket_token, pdf_state

router = APIRouter()


@router.post("/api/load-pdf")
async def load_pdf(
    data: dict,
    x_api_key: Optional[str] = Header(None)
) -> JSONResponse:
    """Load a new PDF file dynamically.
    
    Updates the server's current PDF file and broadcasts a reload
    to all connected WebSocket clients. Optionally configures inverse
    search command for Shift+Click to editor functionality.
    
    Args:
        data: JSON payload with PDF path and optional inverse search config
            - pdf_path (str): Absolute or relative path to PDF file
            - inverse_search_command (str, optional): Editor command template
              with %{line} and %{file} placeholders (e.g., 'nvr --remote-silent +%{line} %{file}')
        x_api_key: API key from X-API-Key header
    
    Returns:
        JSONResponse: Success status with websocket_token if inverse search enabled
    
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
    
    # Handle inverse search configuration (only with HTTPS)
    inverse_search_command = data.get("inverse_search_command")
    if inverse_search_command and settings.use_https:
        # Enable inverse search (token is already generated at server startup)
        pdf_state.inverse_search_enabled = True
        pdf_state.inverse_search_command = inverse_search_command
    elif inverse_search_command and not settings.use_https:
        # Inverse search requires HTTPS - ignore the command but continue
        # Don't fail, just silently disable inverse search
        pdf_state.inverse_search_enabled = False
        pdf_state.inverse_search_command = None
    
    # Broadcast reload to all connected clients
    await manager.broadcast({
        "action": "reload",
        "pdf_mtime": pdf_state.pdf_mtime
    })
    
    response_data = {
        "status": "success",
        "pdf_file": str(pdf_path),
        "filename": pdf_path.name,
        "changed": True
    }
    
    # Include token in response if inverse search is enabled
    if pdf_state.inverse_search_enabled:
        response_data["websocket_token"] = pdf_state.websocket_token
        response_data["inverse_search_enabled"] = True
    
    return JSONResponse(content=response_data)
