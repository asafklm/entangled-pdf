"""Sync client library for PdfServer.

This module provides utility functions for loading PDFs and performing
forward search via SyncTeX. These functions are used by the 
pdf-server sync CLI command.
"""

import http.client
import json
import os
import ssl
import urllib.request
from pathlib import Path
from typing import Optional

import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(InsecureRequestWarning)

DEFAULT_PORT = 8431


def get_server_url(port: int = DEFAULT_PORT, use_http: bool = False) -> str:
    """Get server base URL for given port and protocol.
    
    Args:
        port: Server port number
        use_http: Use HTTP instead of HTTPS
        
    Returns:
        Server base URL string
    """
    protocol = "http" if use_http else "https"
    return f"{protocol}://localhost:{port}"


def create_ssl_context() -> ssl.SSLContext:
    """Create SSL context that allows self-signed certificates."""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def send_request(
    method: str,
    path: str,
    port: int,
    data: Optional[dict] = None,
    api_key: Optional[str] = None,
    use_http: bool = False
) -> dict:
    """Send HTTP request to the server.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        port: Server port
        data: Optional JSON data to send
        api_key: Optional API key for authentication
        use_http: Use HTTP instead of HTTPS
        
    Returns:
        JSON response as dictionary
        
    Raises:
        Exception: If request fails
    """
    protocol = "http" if use_http else "https"
    url = f"{protocol}://localhost:{port}{path}"
    
    # Build request
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    
    if data:
        body = json.dumps(data).encode('utf-8')
    else:
        body = None
    
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method
    )
    
    # Create SSL context
    if not use_http:
        ssl_context = create_ssl_context()
    else:
        ssl_context = None
    
    # Send request
    try:
        response = urllib.request.urlopen(
            request,
            context=ssl_context,
            timeout=10
        )
        return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        if e.code == 403:
            # Provide actionable error message for authentication failures
            raise Exception(
                f"Authentication failed (HTTP 403). "
                f"Ensure PDF_SERVER_API_KEY matches on both client and server. "
                f"Restart server after setting the environment variable."
            )
        raise Exception(f"HTTP {e.code}: {error_body}")
    except Exception as e:
        raise Exception(f"Request failed: {e}")


def load_pdf(pdf_path: Path, port: int, api_key: Optional[str] = None, use_http: bool = False) -> dict:
    """Load a PDF file onto the server.
    
    Args:
        pdf_path: Path to PDF file
        port: Server port
        api_key: Optional API key
        use_http: Use HTTP instead of HTTPS
        
    Returns:
        Server response
    """
    # Resolve to absolute path
    pdf_path = pdf_path.resolve()
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    data = {"pdf_path": str(pdf_path)}
    
    return send_request(
        "POST",
        "/api/load-pdf",
        port,
        data=data,
        api_key=api_key,
        use_http=use_http
    )


def forward_search(
    line: int,
    column: int,
    tex_file: str,
    pdf_file: str,
    port: int,
    api_key: Optional[str] = None,
    use_http: bool = False
) -> dict:
    """Perform forward search via webhook.

    Args:
        line: Line number in source file
        column: Column number in source file
        tex_file: Path to TeX source file
        pdf_file: Path to PDF file (must match currently loaded PDF)
        port: Server port
        api_key: Optional API key
        use_http: Use HTTP instead of HTTPS

    Returns:
        Server response
    """
    # Resolve PDF path to absolute (like load_pdf does)
    pdf_path = Path(pdf_file).resolve()
    
    data = {
        "line": line,
        "col": column,
        "tex_file": tex_file,
        "pdf_file": str(pdf_path)
    }

    return send_request(
        "POST",
        "/webhook/update",
        port,
        data=data,
        api_key=api_key,
        use_http=use_http
    )


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
