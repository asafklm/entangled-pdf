"""Main entry point for PdfServer.

Initializes the FastAPI application, configures settings, and starts the server.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.certs import ensure_certs_exist, get_cert_paths, validate_certificate
from src.config import init_settings
from src.routes import pdf, state, static_files, view, webhook, websocket


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def validate_ssl_config(settings) -> Optional[dict]:
    """Validate SSL configuration and return uvicorn SSL kwargs or None.
    
    Args:
        settings: Application settings instance
        
    Returns:
        SSL config dict for uvicorn, or None if using HTTP
        
    Raises:
        RuntimeError: If HTTPS is required but certificates are missing/invalid
    """
    if not settings.use_https:
        return None
    
    # Determine cert paths
    cert_path = settings.ssl_cert or get_cert_paths()[0]
    key_path = settings.ssl_key or get_cert_paths()[1]
    
    # Check existence
    if not cert_path.exists() or not key_path.exists():
        raise RuntimeError(
            f"SSL certificates not found.\n\n"
            f"Expected at:\n"
            f"  Certificate: {cert_path}\n"
            f"  Private key: {key_path}\n\n"
            f"To generate certificates, run:\n"
            f"  python -m src.certs generate\n\n"
            f"To use custom certificates:\n"
            f"  python main.py --ssl-cert /path/to/cert.pem --ssl-key /path/to/key.pem\n\n"
            f"To bypass HTTPS (not recommended):\n"
            f"  python main.py --http"
        )
    
    # Check expiration
    info = validate_certificate(cert_path)
    if info.get("expired"):
        raise RuntimeError(
            f"SSL certificate has expired ({cert_path})\n\n"
            f"Expired on: {info.get('expires_at')}\n\n"
            f"To regenerate:\n"
            f"  python -m src.certs generate --force\n\n"
            f"To bypass HTTPS (not recommended):\n"
            f"  python main.py --http"
        )
    
    if info.get("error") and not info.get("exists"):
        raise RuntimeError(
            f"Certificate validation failed: {info['error']}\n\n"
            f"To regenerate:\n"
            f"  python -m src.certs generate --force\n\n"
            f"To bypass HTTPS (not recommended):\n"
            f"  python main.py --http"
        )
    
    return {"ssl_keyfile": str(key_path), "ssl_certfile": str(cert_path)}


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
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use HTTP instead of HTTPS (not recommended)"
    )
    parser.add_argument(
        "--ssl-cert",
        type=Path,
        help="Path to SSL certificate file (PEM format)"
    )
    parser.add_argument(
        "--ssl-key",
        type=Path,
        help="Path to SSL private key file (PEM format)"
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
            port=port,
            use_https=not args.http,
            ssl_cert=args.ssl_cert,
            ssl_key=args.ssl_key
        )
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Validate SSL configuration
    try:
        ssl_config = validate_ssl_config(settings)
    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)
    
    protocol = "https" if ssl_config else "http"
    logger.info(f"Starting PdfServer on {settings.host}:{settings.port}")
    logger.info(f"Serving PDF: {settings.pdf_file}")
    logger.info(f"View at: {protocol}://{settings.host}:{settings.port}/view")
    
    if ssl_config:
        logger.info("Note: First-time browser access will show a certificate warning")
        logger.info("      Click 'Advanced' → 'Accept' or 'Proceed' to continue")
    
    # Create app and start server
    app = create_app()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
        **ssl_config if ssl_config else {}
    )


if __name__ == "__main__":
    main()
