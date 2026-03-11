"""WebSocket endpoint for real-time PDF synchronization.

Handles client connections with token authentication and listens for incoming messages
including inverse search requests from authenticated clients.
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from pdfserver.connection_manager import manager
from pdfserver.state import pdf_state
from pdfserver.websocket_monitor import monitor as ws_monitor

router = APIRouter()
logger = logging.getLogger(__name__)


async def run_synctex_edit(
    page: int,
    x: float,
    y: float,
    pdf_path: str
) -> Optional[dict]:
    """Run synctex edit command to get source file coordinates from PDF position.
    
    Args:
        page: Page number in PDF
        x: X coordinate in PDF points
        y: Y coordinate in PDF points
        pdf_path: Path to PDF file
    
    Returns:
        Dictionary with Input (file path), Line, and Column, or None if failed
    """
    try:
        # Run synctex edit command: page:x:y:pdf
        cmd = [
            "synctex",
            "edit",
            "-o",
            f"{page}:{x}:{y}:{pdf_path}"
        ]
        
        logger.debug(f"Running synctex edit: {' '.join(cmd)}")
        
        # Run with timeout and capture output
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)
        
        if process.returncode != 0:
            logger.warning(f"synctex edit failed: {stderr.decode().strip()}")
            return None
        
        # Parse synctex output
        result = {}
        stdout_text = stdout.decode()
        logger.debug(f"synctex edit output:\n{stdout_text}")
        
        for output_line in stdout_text.split("\n"):
            if ":" in output_line:
                key, value = output_line.split(":", 1)
                result[key.strip()] = value.strip()
        
        logger.debug(f"synctex edit parsed result: {result}")
        return result
        
    except (asyncio.TimeoutError, subprocess.TimeoutExpired):
        logger.warning("synctex edit timed out")
        return None
    except Exception as e:
        logger.warning(f"synctex edit error: {e}")
        return None


async def execute_inverse_search(page: int, x: float, y: float) -> bool:
    """Execute inverse search from PDF coordinates to editor.
    
    Args:
        page: Page number
        x: X coordinate in PDF points
        y: Y coordinate in PDF points
    
    Returns:
        True if successful, False otherwise
    """
    if not pdf_state.inverse_search_enabled:
        logger.warning("Inverse search not enabled")
        return False
    
    if not pdf_state.inverse_search_command:
        logger.warning("No inverse search command configured")
        return False
    
    if not pdf_state.pdf_file:
        logger.warning("No PDF file loaded")
        return False
    
    # Check if synctex file exists
    synctex_file = pdf_state.pdf_file.with_suffix(".synctex.gz")
    if not synctex_file.exists():
        # Try without .gz extension
        synctex_file = pdf_state.pdf_file.with_suffix(".synctex")
        if not synctex_file.exists():
            logger.warning(f"No synctex file found for {pdf_state.pdf_file}")
            return False
    
    # Run synctex edit to get source coordinates
    synctex_result = await run_synctex_edit(
        page, x, y, str(pdf_state.pdf_file)
    )
    
    if not synctex_result:
        return False
    
    # Extract source file information
    tex_file = synctex_result.get("Input")
    line = synctex_result.get("Line")
    column = synctex_result.get("Column", "1")
    
    # Handle invalid column values (synctex often returns -1 when column data unavailable)
    try:
        col_num = int(column)
        if col_num < 1:
            column = "1"
    except (ValueError, TypeError):
        column = "1"
    
    if not tex_file or not line:
        logger.warning(f"Invalid synctex result: {synctex_result}")
        return False
    
    # Normalize the file path (remove ./ and resolve to absolute)
    tex_file = str(Path(tex_file).resolve())
    
    # Interpolate command template
    template = pdf_state.inverse_search_command
    command = template.replace("%{line}", line).replace("%{file}", tex_file).replace("%{column}", column)
    
    logger.info(f"Executing inverse search: {command}")
    
    try:
        # Execute the editor command
        # Capture stderr to diagnose issues
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
        
        # Wait briefly and check for immediate errors
        try:
            _, stderr = process.communicate(timeout=2.0)
            if stderr:
                logger.warning(f"Inverse search stderr: {stderr.decode().strip()}")
            if process.returncode != 0:
                logger.error(f"Inverse search command failed with exit code {process.returncode}")
                return False
        except subprocess.TimeoutExpired:
            # Command is still running (expected for nvr), consider it success
            logger.info("Inverse search command started successfully")
            
        return True
    except Exception as e:
        logger.error(f"Failed to execute inverse search command: {e}")
        return False


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None
) -> None:
    """Handle WebSocket connections with token authentication.
    
    Accepts connections with valid tokens and listens for messages including
    inverse search requests. Invalid tokens result in immediate connection closure.
    
    Args:
        websocket: The WebSocket connection
        token: Authentication token from query parameter
    """
    # Validate token if inverse search is enabled
    if pdf_state.inverse_search_enabled:
        if not token:
            await websocket.close(code=4001, reason="Token required")
            return
        
        if token != pdf_state.websocket_token:
            await websocket.close(code=4002, reason="Invalid token")
            return
    
    await manager.connect(websocket)
    
    try:
        # Listen for incoming messages with timeout to detect dead connections
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(), 
                    timeout=30.0  # 30 second timeout - client should ping every 25s
                )
            except asyncio.TimeoutError:
                # No message received in 30 seconds - client should have pinged
                # This is a failsafe to detect dead connections
                logger.debug("WebSocket timeout - no ping received from client")
                break
            
            # Handle ping/pong for connection keepalive (client-authoritative)
            if message.get("action") == "ping":
                ws_monitor.log_receive(message)
                # Echo back timestamp for RTT calculation
                await websocket.send_json({
                    "action": "pong",
                    "timestamp": message.get("timestamp")
                })
                ws_monitor.log_sent({"action": "pong"})
                continue
            
            # Log other received messages
            ws_monitor.log_receive(message)
            
            # Handle client log messages
            if message.get("action") == "log":
                log_msg = message.get("message", "")
                if log_msg:
                    logger.debug(f"[CLIENT] {log_msg}")
                continue
            
            # Handle inverse search requests
            if message.get("action") == "inverse_search":
                if not pdf_state.inverse_search_enabled:
                    logger.warning("Inverse search request received but not enabled")
                    continue
                
                page = message.get("page")
                x = message.get("x")
                y = message.get("y")
                
                if page is None or x is None or y is None:
                    logger.warning("Invalid inverse search request: missing coordinates")
                    continue
                
                # Execute inverse search asynchronously
                await execute_inverse_search(int(page), float(x), float(y))
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Server error")
        except Exception:
            pass
    finally:
        manager.disconnect(websocket)
