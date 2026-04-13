"""Main entry point for EntangledPdf.

Initializes the FastAPI application, configures settings, and starts the server.
Server can be started without a PDF file (PDF is loaded dynamically via API).
Server runs in foreground mode (use Ctrl+C to stop).
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from entangledpdf.certs import get_cert_paths, validate_certificate
from entangledpdf.config import init_settings, ConfigError
from entangledpdf.logging_sanitizer import SensitiveDataFilter
from entangledpdf.routes import auth, load_pdf, pdf, state, static_files, test_utils, view, webhook, websocket
from entangledpdf.state import pdf_state
from entangledpdf.websocket_monitor import monitor as ws_monitor


# Configure logging for foreground mode
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger().addFilter(SensitiveDataFilter())
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
            f"  python -m entangledpdf.certs generate\n\n"
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
            f"  python -m entangledpdf.certs generate --force\n\n"
            f"To bypass HTTPS (not recommended):\n"
            f"  python main.py --http"
        )
    
    if info.get("error") and not info.get("exists"):
        raise RuntimeError(
            f"Certificate validation failed: {info['error']}\n\n"
            f"To regenerate:\n"
            f"  python -m entangledpdf.certs generate --force\n\n"
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
        title="EntangledPdf",
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
    app.include_router(test_utils.router)
    
    # Setup static files
    static_files.setup_static_files(app)
    
    return app


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="EntangledPdf - Real-time PDF synchronization server",
        epilog="PDF files are loaded dynamically via the entangle-pdf sync command. "
               "Server can be started without a PDF file."
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Server port (default: 8431 or ENTANGLEDPDF_PORT env var)"
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for authentication (default: ENTANGLEDPDF_API_KEY env var)"
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
        help="Inverse search command template with %%{line}, %%{column}, and %%{file} placeholders "
             "(e.g., 'nvr --remote-silent -c \"call cursor(%%{line}, %%{column})\" %%{file}')"
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


def check_vim_clientserver() -> bool:
    """Check if vim supports the --servername option.
    
    Returns:
        True if vim supports clientserver features, False otherwise
    """
    try:
        result = subprocess.run(
            ["vim", "--servername", "TEST", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=5
        )
        # If vim doesn't support --servername, it returns error
        return result.returncode == 0 and b"Unknown option argument" not in result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_inverse_search_command(args) -> str | None:
    """Determine inverse search command from arguments.
    
    Args:
        args: Parsed command line arguments
    
    Returns:
        Command template string or None if inverse search not enabled
    
    Raises:
        SystemExit: If vim is requested but doesn't support clientserver features
    """
    if args.inverse_search_command:
        # User provided custom command - unescape %% to %
        return args.inverse_search_command.replace("%%", "%")
    elif args.inverse_search_nvim:
        return "nvr --nostart --remote-silent %{file} -c 'call cursor(%{line}, %{column})'"
    elif args.inverse_search_vim:
        if not check_vim_clientserver():
            print("ERROR: Vim does not support --servername (clientserver features not available).")
            print("This is common on minimal Vim installations (vim.basic).")
            print("")
            print("Options:")
            print("1. Install Neovim and use --inverse-search-nvim instead:")
            print("   apt install neovim")
            print("   pip install neovim-remote")
            print("")
            print("2. Install a fuller Vim with clientserver support:")
            print("   apt install vim-gtk3  # or vim-nox")
            print("")
            print("3. Use a custom inverse search command:")
            print("   entangle-pdf start --inverse-search-command 'your-command %{file} %{line}'")
            sys.exit(1)
        return "vim --servername VIM --remote-silent %{file} '+call cursor(%{line}, %{column})'"
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
            api_key=args.api_key,
            use_https=not args.http,
            ssl_cert=args.ssl_cert,
            ssl_key=args.ssl_key
        )
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Report API key source
    import os
    if os.getenv("ENTANGLEDPDF_API_KEY"):
        print("API key loaded from ENTANGLEDPDF_API_KEY environment variable", flush=True)
    
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
    
    logger.info(f"Starting EntangledPdf on {settings.host}:{settings.port}")
    logger.info("No PDF loaded - waiting for entangle-pdf sync to load a PDF")
    
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
