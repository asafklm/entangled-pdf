"""Webhook endpoint for receiving PDF position updates.

Receives SyncTeX forward search coordinates and broadcasts them
 to all connected WebSocket clients.
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from pdfserver.config import get_settings
from pdfserver.connection_manager import manager
from pdfserver.state import pdf_state

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
        
        logger.info(f"Running synctex command: {' '.join(cmd)}")
        
        # Run with timeout and capture output
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)
        
        stdout_str = stdout.decode()
        stderr_str = stderr.decode()
        
        logger.info(f"Synctex stdout: {stdout_str}")
        if stderr_str:
            logger.info(f"Synctex stderr: {stderr_str}")
        
        if process.returncode != 0:
            logger.warning(f"synctex failed with returncode {process.returncode}: {stderr_str.strip()}")
            return None
        
        # Parse synctex output
        result = {}
        for output_line in stdout_str.split('\n'):
            if ':' in output_line:
                key, value = output_line.split(':', 1)
                result[key.strip()] = value.strip()
        
        # Check for warnings in result
        if 'SyncTeX Warning' in result:
            logger.warning(f"Synctex warning: {result.get('SyncTeX Warning')}")
        
        # Validate required keys exist
        required_keys = ['Page', 'x', 'y']
        missing_keys = [k for k in required_keys if k not in result]
        if missing_keys:
            logger.warning(f"Synctex result missing required keys: {missing_keys}. Result: {result}")
            return None
        
        # Validate coordinates are meaningful (not all zeros)
        try:
            page = int(result.get('Page', 0))
            x = float(result.get('x', 0))
            y = float(result.get('y', 0))
            
            if page <= 0 or x <= 0 or y <= 0:
                logger.warning(f"Synctex returned invalid coordinates: page={page}, x={x}, y={y}")
                return None
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse synctex coordinates: {e}. Result: {result}")
            return None
        
        logger.info(f"Synctex successful: page={page}, x={x}, y={y}")
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
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=403,
            detail="Authentication failed. Ensure PDF_SERVER_API_KEY is set and server was restarted."
        )
    
    logger.info(f"Webhook received: {data}")
    
    # Extract and validate required parameters
    required_fields = ["line", "col", "tex_file", "pdf_file"]
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(missing_fields)}"
        )
    
    # Validate field types and values
    try:
        line = int(data["line"])
        col = int(data["col"])
        tex_file = data["tex_file"]
        pdf_file = data["pdf_file"]
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid parameter value: {e}"
        )
    
    # Normalize PDF file path
    pdf_path = Path(pdf_file)
    if not pdf_path.is_absolute():
        pdf_path = (settings.static_dir / pdf_path).resolve()
    
    # Run synctex to get PDF coordinates
    logger.info(f"Running synctex: line={line}, col={col}, tex_file={tex_file}, pdf_path={pdf_path}")
    synctex_result = await run_synctex_view(line, col, tex_file, pdf_path)
    
    if synctex_result:
        # Successful synctex lookup - coordinates already validated in run_synctex_view
        page = int(synctex_result["Page"])
        y = float(synctex_result["y"])
        x = float(synctex_result["x"])
        
        # Update global state with x coordinate for reconnecting clients
        pdf_state.update(page, y, x)
        
        # Broadcast to all connected clients
        logger.info(f"Broadcasting synctex to {len(manager.active_connections)} clients: page={page}, y={y}, x={x}")
        await manager.broadcast({
            "action": "synctex",
            "page": page,
            "y": y,
            "x": x,
            "last_sync_time": pdf_state.last_sync_time
        })
        
        return JSONResponse(content={
            "status": "success",
            "page": page,
            "y": y,
            "x": x
        })
    else:
        # Synctex failed - don't scroll
        logger.warning(f"Synctex lookup failed for {tex_file}:{line}:{col} -> {pdf_path}")
        return JSONResponse(content={
            "status": "error",
            "page": None,
            "message": "Synctex lookup failed, no scroll performed"
        }, status_code=400)
