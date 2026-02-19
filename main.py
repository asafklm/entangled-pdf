"""Main entry point for PdfServer.

Initializes the FastAPI application, configures settings, and starts the server.
"""

import argparse
import logging
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.config import init_settings
from src.routes import pdf, state, static_files, view, webhook, websocket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="PdfServer",
        description="Real-time PDF synchronization server with SyncTeX support",
        version="1.0.0"
    )
    
    # Include all routes
    app.include_router(view.router)
    app.include_router(pdf.router)
    app.include_router(state.router)
    app.include_router(webhook.router)
    app.include_router(websocket.router)
    
    # Setup static files
    static_files.setup_static_files(app)
    
    return app


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="PdfServer - Real-time PDF synchronization server"
    )
    parser.add_argument(
        "pdf_file",
        help="Path to the PDF file to serve"
    )
    parser.add_argument(
        "port_arg",
        nargs="?",
        help="Port in format port=8001 (optional, defaults to PDF_SERVER_PORT env var or 8431)"
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    # Parse port from argument if provided
    port = None
    if args.port_arg:
        try:
            port = int(args.port_arg.split("=")[1])
        except (IndexError, ValueError):
            logger.error(f"Invalid port argument: {args.port_arg}")
            logger.error("Expected format: port=8001")
            sys.exit(1)
    
    # Initialize settings
    try:
        settings = init_settings(
            pdf_file=Path(args.pdf_file),
            port=port
        )
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    logger.info(f"Starting PdfServer on {settings.host}:{settings.port}")
    logger.info(f"Serving PDF: {settings.pdf_file}")
    logger.info(f"View at: http://{settings.host}:{settings.port}/view")
    
    # Create app and start server
    app = create_app()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
