"""
A simple HTTP server that serves a single PDF file.

This script creates a basic HTTP server that serves a single PDF file to clients.
The server listens on port 8000 by default and serves the specified PDF file.
Clients can access the PDF file by visiting the server's IP address.

Usage:
    python3 pdf_server.py
"""
import socket
import socketserver

from http.server import SimpleHTTPRequestHandler

PORT: int = 8001
PDF_FILE: str = "example.pdf"  # Replace 'example.pdf' with the path to your PDF file


class PDFHandler(SimpleHTTPRequestHandler):
    """
    Custom handler to serve only the PDF file

    Args:
        SimpleHTTPRequestHandler: Base class for handling HTTP requests
    """

    def __init__(self: "PDFHandler", *args: str, **kwargs: str) -> None:
        """
        Initialize the PDFHandler.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.path: str = PDF_FILE

    def end_headers(self: "PDFHandler") -> None:
        """
        Add Content-Disposition header for inline PDF viewing.
        """
        self.send_header("Content-Disposition", f'inline; filename*="{PDF_FILE}#page=2"')
        super().end_headers()

    def do_GET(self: "PDFHandler") -> None:
        """
        Handle GET request.
        """
        if self.path == "/":
            self.path = PDF_FILE
        super().do_GET()


# Get the local IP address


def get_ip() -> str:
    """
    Get the local IP address.

    Returns:
        str: Local IP address.
    """
    return socket.gethostbyname(socket.gethostname())


def serve() -> None:
    """
    Start the HTTP server.
    """
    with socketserver.TCPServer(("", PORT), PDFHandler) as httpd:
        print(f"Serving at IP: {get_ip()}, port: {PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    serve()
