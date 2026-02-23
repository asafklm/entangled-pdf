"""Webhook endpoint for receiving PDF position updates.

Receives SyncTeX forward search coordinates and broadcasts them
 to all connected WebSocket clients.
"""

import asyncio
import logging
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.connection_manager import manager
from src.state import pdf_state

router = APIRouter()

logger = logging.getLogger(__name__)


async def run_synctex_view(
    line: int,
    col: int,
    tex_file: str,
    pdf_path: Path
) -> Optional[Dict[str, Any]]:
    """Run synctex view command to get PDF coordinates from line:column.
    
    Args:
        line: Line number in TeX file
        col: Column number in TeX file
        tex_file: Path to TeX source file
        pdf_path: Path to PDF file
    
    Returns:
        Dictionary with synctex results or None if failed
    """
    try:
        # Run synctex command
        cmd = [
            "synctex",
            "view",
            "-i", f"{line}:{col}:{tex_file}",
            "-o", str(pdf_path)
        ]
        
        # Run with timeout and capture output
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)
        
        if process.returncode != 0:
            logger.warning(f"synctex failed: {stderr.decode().strip()}")
            return None
        
        # Parse synctex output
        result = {}
        for line in stdout.decode().split('\n'):
            if isinstance(line, str) and ":" in line:
                key, value = line.split(":", 1)
                result[key.strip()] = value.strip()
        
        return result
        
    except (asyncio.TimeoutError, subprocess.TimeoutExpired):
        logger.warning("synctex timed out")
        return None
    except Exception as e:
        logger.warning(f"synctex error: {e}")
        return None


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


@router.post("/webhook/synctex")
async def receive_synctex_update(
    data: dict,
    x_api_key: Optional[str] = Header(None)
) -> JSONResponse:
    """Receive Synctex coordinates from VimTeX and broadcast to clients.
    
    Converts line:column coordinates to PDF page and y-coordinate using synctex.
    If synctex fails and PDF was updated, triggers client-side PDF reload.
    
    Args:
        data: JSON payload with TeX coordinates
            - line (int): Line number in TeX file (required)
            - col (int): Column number in TeX file (required)
            - tex_file (str): Path to TeX source file (required)
            - pdf_file (str): Path to PDF file (required)
        x_api_key: API key from X-API-Key header
    
    Returns:
        JSONResponse: Success status with PDF coordinates or None
    
    Raises:
        HTTPException: 403 if API key is invalid
        HTTPException: 400 if required parameters are missing or invalid
    """
    settings = get_settings()
    
    # Validate API key
    if x_api_key != settings.secret:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Extract and validate parameters
    try:
        line = int(data["line"])
        col = int(data["col"])
        tex_file = data["tex_file"]
        pdf_file = data["pdf_file"]
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameters: {e}")
    
    # Normalize PDF file path
    pdf_path = Path(pdf_file)
    if not pdf_path.is_absolute():
        pdf_path = (settings.static_dir / pdf_path).resolve()
    
    # Run synctex to get PDF coordinates
    synctex_result = await run_synctex_view(line, col, tex_file, pdf_path)
    
    if synctex_result:
        # Successful synctex lookup - extract coordinates
        try:
            page = int(synctex_result.get("Page", 0))
            y = float(synctex_result.get("y", 0))
            x = float(synctex_result.get("x", 0))
            
            # Update global state
            pdf_state.update(page, y)
            
            # Broadcast to all connected clients
            await manager.broadcast({
                "action": "synctex",
                "page": page,
                "y": y,
                "x": x,
                "timestamp": pdf_state.last_update_time
            })
            
            return JSONResponse(content={
                "status": "success",
                "page": page,
                "y": y,
                "x": x
            })
            
        except (ValueError, TypeError):
            # Invalid coordinate values
            logger.warning(f"Invalid synctex coordinates: {synctex_result}")
            return JSONResponse(content={
                "status": "error",
                "message": "Invalid coordinate values",
                "page": None
            })
    else:
        # Synctex failed - check if PDF needs reload
        try:
            current_mtime = pdf_path.stat().st_mtime
            if current_mtime > settings.pdf_file.stat().st_mtime:
                # PDF was updated - trigger reload
                await manager.broadcast({
                    "action": "reload",
                    "timestamp": time.time()
                })
                
                return JSONResponse(content={
                    "status": "success",
                    "message": "PDF updated, triggering reload",
                    "page": None
                })
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning(f"Error checking PDF mtime: {e}")
        
        # Return success with empty result
        return JSONResponse(content={
            "status": "success",
            "page": None
        })