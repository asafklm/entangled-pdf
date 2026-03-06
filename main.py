"""Main entry point for PdfServer.

Initializes the FastAPI application, configures settings, and starts the server.
Server can be started without a PDF file (PDF is loaded dynamically via API).
Server runs in foreground mode (use Ctrl+C to stop).
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

from src.certs import get_cert_paths, validate_certificate
from src.config import init_settings
from src.routes import auth, load_pdf, pdf, state, static_files, view, webhook, websocket
from src.state import pdf_state
from src.websocket_monitor import monitor as ws_monitor


# Configure logging for foreground mode
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
    app.include_router(auth.router)
    app.include_router(view.router)
    app.include_router(pdf.router)
    app.include_router(state.router)
    app.include_router(webhook.router)
    app.include_router(websocket.router)
    app.include_router(load_pdf.router)
    
    # Setup static files
    static_files.setup_static_files(app)
    
    return app


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="PdfServer - Real-time PDF synchronization server",
        epilog="PDF files are loaded dynamically via the sync-remote-pdf tool. "
               "Server can be started without a PDF file."
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Server port (default: 8431 or PDF_SERVER_PORT env var)"
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
    
    # Inverse search configuration (can only be set at startup)
    inverse_group = parser.add_mutually_exclusive_group()
    
    inverse_group.add_argument(
        "--inverse-search-command",
        type=str,
        metavar="CMD",
        help="Inverse search command template with %%{line} and %%{file} placeholders "
             "(e.g., 'nvr --remote-silent +%%{line} %%{file}')"
    )
    
    inverse_group.add_argument(
        "--inverse-search-nvim",
        action="store_true",
        help="Enable inverse search for Neovim (uses nvr --nostart --remote-silent)"
    )
    
    inverse_group.add_argument(
        "--inverse-search-vim",
        action="store_true",
        help="Enable inverse search for Vim (uses vim --remote-silent)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging and WebSocket monitoring"
    )
    
    parser.add_argument(
        "--log-file",
        metavar="FILE",
        type=Path,
        default=None,
        help="Write logs to file in addition to stdout"
    )
    
    return parser.parse_args()


def get_inverse_search_command(args) -> str | None:
    """Determine inverse search command from arguments.
    
    Args:
        args: Parsed command line arguments
    
    Returns:
        Command template string or None if inverse search not enabled
    """
    if args.inverse_search_command:
        # User provided custom command - unescape %% to %
        return args.inverse_search_command.replace("%%", "%")
    elif args.inverse_search_nvim:
        return "nvr --nostart --remote-silent +%{line} %{file}"
    elif args.inverse_search_vim:
        return "vim --servername VIM --remote-silent +%{line} %{file}"
    else:
        return None


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    # Parse port
    port = args.port
    
    # Get inverse search command
    inverse_command = get_inverse_search_command(args)
    
    try:
        settings = init_settings(
            pdf_file=None,  # PDF is loaded dynamically
            port=port,
            use_https=not args.http,
            ssl_cert=args.ssl_cert,
            ssl_key=args.ssl_key
        )
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Set log level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Add file handler if log file specified
    if args.log_file:
        try:
            file_handler = logging.FileHandler(args.log_file, mode='a')
            file_handler.setLevel(logging.DEBUG if args.verbose else logging.INFO)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(formatter)
            logging.getLogger().addHandler(file_handler)
            logger.info(f"Logging to file: {args.log_file}")
        except Exception as e:
            logger.warning(f"Failed to open log file {args.log_file}: {e}")
    
    # Enable WebSocket monitoring when verbose
    if args.verbose:
        ws_monitor.enable()
        logger.info("WebSocket monitoring enabled")
    
    # Validate SSL configuration
    try:
        ssl_config = validate_ssl_config(settings)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    
    # Configure inverse search
    if inverse_command:
        if ssl_config:
            # Only enable inverse search with HTTPS/WSS
            pdf_state.inverse_search_command = inverse_command
            pdf_state.inverse_search_enabled = True
            logger.info(f"Inverse search enabled: {inverse_command}")
        else:
            # HTTP mode - can't enable inverse search
            logger.warning("Inverse search requires HTTPS. Command ignored.")
            pdf_state.inverse_search_enabled = False
    else:
        pdf_state.inverse_search_enabled = False
    
    logger.info(f"Starting PdfServer on {settings.host}:{settings.port}")
    logger.info("No PDF loaded - waiting for sync-remote-pdf to load a PDF")
    
    # Print startup banner to stdout (visible before daemonization)
    if ssl_config and pdf_state.inverse_search_enabled:
        # HTTPS with inverse search
        print(f"\n{'='*60}")
        print(f"PDF Server Ready")
        print(f"Inverse search: {inverse_command}")
        print(f"{'='*60}")
        print(f"URL:    https://localhost:{settings.port}/view")
        print(f"Token:  {pdf_state.websocket_token}")
        print(f"{'='*60}")
        print("Copy the token to your browser to enable inverse search")
        print(f"{'='*60}\n")
    elif ssl_config:
        # HTTPS without inverse search
        print(f"\n{'='*60}")
        print(f"PDF Server Ready (HTTPS)")
        print(f"{'='*60}")
        print(f"URL:    https://localhost:{settings.port}/view")
        print(f"Token:  {pdf_state.websocket_token}")
        print(f"{'='*60}")
        print("Copy the token to your browser")
        print(f"{'='*60}\n")
    else:
        # HTTP mode
        print(f"\n{'='*60}")
        print(f"PDF Server Ready (HTTP)")
        print(f"{'='*60}")
        print(f"URL:    http://localhost:{settings.port}/view")
        print(f"{'='*60}\n")
        logger.warning("Running in HTTP mode - inverse search is disabled for security")
    
    # Create app and start server
    app = create_app()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info" if args.verbose else "warning",
        timeout_keep_alive=30,  # Send TCP keepalive every 30 seconds
        **ssl_config if ssl_config else {}
    )


if __name__ == "__main__":
    main()
