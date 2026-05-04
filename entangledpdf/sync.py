"""Sync client library for EntangledPdf.

This module provides utility functions for loading PDFs and performing
forward search via SyncTeX using Unix domain sockets for communication
with the local server.

No API key or SSL configuration is required - authentication is provided
by filesystem permissions on the Unix socket (mode 0600).
"""

import http.client
import json
import socket as socket_module
from pathlib import Path
from typing import Optional

from entangledpdf.socket_path import get_socket_path


def get_default_socket_path() -> Path:
    """Get the default Unix socket path for server communication.
    
    Returns:
        Path to the Unix socket file
    """
    return get_socket_path()


class UnixHTTPConnection(http.client.HTTPConnection):
    """HTTP connection over Unix domain socket.
    
    Overrides the connect() method to use a Unix socket instead of TCP.
    """
    
    def __init__(self, socket_path: str):
        """Initialize connection to Unix socket.
        
        Args:
            socket_path: Path to the Unix socket file
        """
        super().__init__("localhost")
        self.socket_path = socket_path
    
    def connect(self) -> None:
        """Connect to the Unix socket."""
        self.sock = socket_module.socket(socket_module.AF_UNIX, socket_module.SOCK_STREAM)
        self.sock.connect(self.socket_path)


def send_request(
    method: str,
    path: str,
    socket_path: Path,
    data: Optional[dict] = None
) -> dict:
    """Send HTTP request to the server via Unix socket.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        socket_path: Path to Unix socket
        data: Optional JSON data to send
        
    Returns:
        JSON response as dictionary
        
    Raises:
        FileNotFoundError: If socket does not exist (server not running)
        ConnectionRefusedError: If server is not accepting connections
        Exception: If request fails
    """
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None
    
    conn = UnixHTTPConnection(str(socket_path))
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        response_body = response.read().decode("utf-8")
        
        if response.status >= 400:
            raise Exception(f"HTTP {response.status}: {response_body}")
        
        return json.loads(response_body)
    except (FileNotFoundError, ConnectionRefusedError):
        raise
    except Exception as e:
        raise Exception(f"Request failed: {e}")
    finally:
        conn.close()


def load_pdf(pdf_path: Path, socket_path: Optional[Path] = None) -> dict:
    """Load a PDF file onto the server.
    
    Args:
        pdf_path: Path to PDF file
        socket_path: Path to Unix socket (uses default if not specified)
        
    Returns:
        Server response
        
    Raises:
        FileNotFoundError: If PDF file not found or server not running
    """
    socket_path = socket_path or get_default_socket_path()
    
    # Resolve to absolute path
    pdf_path = pdf_path.resolve()
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    data = {"pdf_path": str(pdf_path)}
    
    return send_request("POST", "/api/load-pdf", socket_path, data)


def forward_search(
    line: int,
    column: int,
    tex_file: str,
    pdf_file: str,
    socket_path: Optional[Path] = None
) -> dict:
    """Perform forward search via webhook.

    Args:
        line: Line number in source file
        column: Column number in source file
        tex_file: Path to TeX source file
        pdf_file: Path to PDF file (must match currently loaded PDF)
        socket_path: Path to Unix socket (uses default if not specified)

    Returns:
        Server response
    """
    socket_path = socket_path or get_default_socket_path()
    
    # Resolve PDF path to absolute
    pdf_path = Path(pdf_file).resolve()
    
    data = {
        "line": line,
        "col": column,
        "tex_file": tex_file,
        "pdf_file": str(pdf_path)
    }

    return send_request("POST", "/webhook/update", socket_path, data)


def get_server_state(socket_path: Optional[Path] = None) -> Optional[dict]:
    """Get current server state.
    
    Args:
        socket_path: Path to Unix socket (uses default if not specified)
        
    Returns:
        Server state dictionary, or None if server not running
    """
    socket_path = socket_path or get_default_socket_path()
    
    try:
        return send_request("GET", "/state", socket_path)
    except (FileNotFoundError, ConnectionRefusedError):
        return None


def parse_synctex_forward(value: str) -> tuple[int, int, str]:
    """Parse synctex forward argument.
    
    Args:
        value: String in format "line:column:file"
        
    Returns:
        Tuple of (line, column, file)
        
    Raises:
        ValueError: If format is invalid
    """
    parts = value.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid synctex format: {value}. Expected: line:column:file")
    
    try:
        line = int(parts[0])
        column = int(parts[1])
    except ValueError:
        raise ValueError(f"Line and column must be integers: {value}")
    
    return line, column, parts[2]
