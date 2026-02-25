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
        for output_line in stdout.decode().split('\n'):
            if ":" in output_line:
                key, value = output_line.split(":", 1)
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
    
    Always attempts to use synctex to convert TeX coordinates to PDF coordinates.
    If synctex succeeds, broadcasts the PDF position. If synctex fails or no
    TeX coordinates are provided, simply returns success without scrolling.
    
    Args:
        data: JSON payload with TeX coordinates
            - line (int): Line number in TeX file
            - col (int): Column number in TeX file  
            - tex_file (str): Path to TeX source file
            - pdf_file (str): Path to PDF file
        x_api_key: API key from X-API-Key header
    
    Returns:
        JSONResponse: Success status with PDF coordinates or None if synctex failed
    
    Raises:
        HTTPException: 403 if API key is invalid
    """
    settings = get_settings()
    
    # Validate API key
    if x_api_key != settings.secret:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Extract parameters
    try:
        line = int(data["line"])
        col = int(data["col"])
        tex_file = data["tex_file"]
        pdf_file = data["pdf_file"]
    except (ValueError, TypeError, KeyError) as e:
        # Missing or invalid synctex parameters - don't scroll, just return success
        return JSONResponse(content={
            "status": "success",
            "page": None,
            "message": "No valid synctex parameters, no scroll performed"
        })
    
    # Normalize PDF file path
    pdf_path = Path(pdf_file)
    if not pdf_path.is_absolute():
        pdf_path = (settings.static_dir / pdf_path).resolve()
    
    # Run synctex to get PDF coordinates
    synctex_result = await run_synctex_view(line, col, tex_file, pdf_path)
    
    if synctex_result:
        # Successful synctex lookup - extract coordinates and broadcast
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
            # Invalid coordinate values - don't scroll
            logger.warning(f"Invalid synctex coordinates: {synctex_result}")
            return JSONResponse(content={
                "status": "success",
                "page": None,
                "message": "Invalid synctex coordinates, no scroll performed"
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
        
        # Synctex failed and no PDF update - don't scroll
        return JSONResponse(content={
            "status": "success",
            "page": None,
            "message": "Synctex lookup failed, no scroll performed"
        })


@router.post("/webhook/shutdown")
async def shutdown_server(
    x_api_key: Optional[str] = Header(None)
) -> JSONResponse:
    """Shutdown the PDF server gracefully.
    
    Authenticates requests using the X-API-Key header and initiates
    a graceful shutdown of the server. This is used by VimTeX when
    switching to a different PDF file.
    
    Args:
        x_api_key: API key from X-API-Key header
    
    Returns:
        JSONResponse: Success status
    
    Raises:
        HTTPException: 403 if API key is invalid
    """
    settings = get_settings()
    
    # Validate API key
    if x_api_key != settings.secret:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    logger.info("Shutdown requested, initiating graceful shutdown...")
    
    # Schedule shutdown after response is sent
    async def do_shutdown():
        await asyncio.sleep(1)  # Give time for response to be sent
        import signal
        import os
        os.kill(os.getpid(), signal.SIGTERM)
    
    asyncio.create_task(do_shutdown())
    
    return JSONResponse(content={
        "status": "success",
        "message": "Server shutting down gracefully"
    })
