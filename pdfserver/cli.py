"""CLI entry point for pdf-server command.

This module provides the main entry point for the pdf-server CLI tool,
which manages the PDF server lifecycle.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import argcomplete
import requests
import urllib3

# Suppress urllib3 warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
DEFAULT_PORT = 8431


def get_server_dir() -> Path:
    """Get the server directory (parent of package)."""
    # When installed via pip, the package is in site-packages
    # We need to find where static files and certs are stored
    import pdfserver
    
    package_dir = Path(pdfserver.__file__).parent.resolve()
    # The server root is one level up from the package
    server_dir = package_dir.parent
    
    # If installed in development mode (pip install -e), files are in the git repo
    # If installed normally, we need to handle this differently
    return server_dir


def get_python_cmd() -> str:
    """Get Python command to use."""
    return sys.executable


def get_server_url(port: int, use_http: bool = False) -> str:
    """Get server base URL."""
    protocol = "http" if use_http else "https"
    return f"{protocol}://localhost:{port}"


def get_server_state(port: int, verify_ssl: bool = False):
    """Check if server is running and get state."""
    try:
        url = f"{get_server_url(port)}/state"
        response = requests.get(url, timeout=2, verify=verify_ssl)
        response.raise_for_status()
        return response.json()
    except Exception:
        # Try HTTP as fallback
        try:
            url = f"http://localhost:{port}/state"
            response = requests.get(url, timeout=2, verify=verify_ssl)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def is_server_running(port: int) -> bool:
    """Check if server is running on given port."""
    return get_server_state(port) is not None


def cmd_start(args):
    """Start the PDF server (foreground mode)."""
    port = args.port or int(os.getenv("PDF_SERVER_PORT", DEFAULT_PORT))
    
    # Check if server already running
    if is_server_running(port):
        print(f"Error: Server already running on port {port}", file=sys.stderr)
        print(f"Use 'pdf-server status --port {port}' to see details", file=sys.stderr)
        print(f"Use 'pdf-server stop --port {port}' for stop instructions", file=sys.stderr)
        return 1
    
    # Find the main.py file
    try:
        import pdfserver
        package_dir = Path(pdfserver.__file__).parent
        main_py = package_dir.parent / "main.py"
        
        # If main.py is not next to the package, try to find it
        if not main_py.exists():
            # When installed via pip -e, main.py should be in the same dir as pdfserver
            main_py = package_dir.parent / "main.py"
        
        if not main_py.exists():
            print("Error: Could not find main.py. Are you in development mode?", file=sys.stderr)
            return 1
    except ImportError:
        print("Error: Could not import pdfserver package", file=sys.stderr)
        return 1
    
    python_cmd = get_python_cmd()
    server_dir = main_py.parent
    
    # Build command
    cmd = [
        python_cmd,
        str(main_py),
        "--port", str(port)
    ]
    
    if args.http:
        cmd.append("--http")
    
    if args.inverse_search_command:
        # Escape % for argparse
        escaped_cmd = args.inverse_search_command.replace("%", "%%")
        cmd.extend(["--inverse-search-command", escaped_cmd])
    elif args.inverse_search_nvim:
        cmd.append("--inverse-search-nvim")
    elif args.inverse_search_vim:
        cmd.append("--inverse-search-vim")
    
    if args.verbose:
        cmd.append("--verbose")
    
    if args.log_file:
        cmd.extend(["--log-file", str(args.log_file)])
    
    if args.api_key:
        cmd.extend(["--api-key", args.api_key])
    
    # Set environment
    env = os.environ.copy()
    env["PDF_SERVER_PORT"] = str(port)
    
    # Run server in foreground - this will block until Ctrl+C
    print(f"Starting PdfServer on port {port}...")
    print("Press Ctrl+C to stop the server\n")
    
    try:
        result = subprocess.run(cmd, cwd=str(server_dir), env=env)
        return result.returncode
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        return 0
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        return 1


def cmd_stop(args):
    """Show instructions for stopping the server."""
    port = args.port or int(os.getenv("PDF_SERVER_PORT", DEFAULT_PORT))
    
    if is_server_running(port):
        print(f"Server is running on port {port}")
        print("\nTo stop the server:")
        print("  Press Ctrl+C in the terminal where you ran 'pdf-server start'")
        print(f"\nOr find the process and kill it:")
        print(f"  kill $(lsof -t -i:{port})")
    else:
        print(f"Server not running on port {port}")
    
    return 0


def cmd_status(args):
    """Show server status."""
    port = args.port or int(os.getenv("PDF_SERVER_PORT", DEFAULT_PORT))
    
    state = get_server_state(port)
    
    if state is None:
        print(f"Server not running on port {port}")
        return 0
    
    # Show status
    print(f"Server running on port {port}")
    print(f"  Status: {'Ready' if state.get('pdf_loaded') else 'Waiting for PDF'})")
    print(f"  PDF: {state.get('pdf_file', 'None')}")
    
    if state.get('pdf_mtime'):
        import datetime
        mtime = datetime.datetime.fromtimestamp(state['pdf_mtime'])
        print(f"  PDF modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Display authentication token if available
    if state.get('websocket_token'):
        print(f"\n  Authentication Token: {state['websocket_token']}")
    
    protocol = "https" if not is_server_running(port) else "https"
    # Check if HTTP mode
    try:
        requests.get(f"http://localhost:{port}/state", timeout=1)
        protocol = "http"
    except:
        pass
    
    print(f"\n  URL: {protocol}://localhost:{port}/view")
    
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PdfServer management tool (foreground mode only)",
        prog="pdf-server"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"Server port (default: {DEFAULT_PORT} or PDF_SERVER_PORT env var)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # start command
    start_parser = subparsers.add_parser("start", help="Start the PDF server (foreground)")
    
    inverse_group = start_parser.add_mutually_exclusive_group()
    inverse_group.add_argument(
        "--inverse-search-command",
        metavar="CMD",
        help="Inverse search command template (e.g., 'nvr --remote-silent +%%{line} %%{file}')"
    )
    inverse_group.add_argument(
        "--inverse-search-nvim",
        action="store_true",
        help="Enable inverse search for Neovim (uses nvr --nostart --remote-silent)"
    )
    inverse_group.add_argument(
        "--inverse-search-vim",
        action="store_true",
        help="Enable inverse search for Vim"
    )
    
    start_parser.add_argument(
        "--http",
        action="store_true",
        help="Use HTTP instead of HTTPS (not recommended)"
    )
    start_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging and WebSocket monitoring"
    )
    
    start_parser.add_argument(
        "--log-file",
        metavar="FILE",
        type=Path,
        default=None,
        help="Write logs to file in addition to stdout"
    )
    
    start_parser.add_argument(
        "--api-key",
        metavar="KEY",
        help="API key for authentication (default: PDF_SERVER_API_KEY env var)"
    )
    
    # stop command
    subparsers.add_parser("stop", help="Show how to stop the PDF server")
    
    # status command
    subparsers.add_parser("status", help="Show server status")
    
    # Enable bash completion
    argcomplete.autocomplete(parser)
    
    args = parser.parse_args()
    
    if args.command == "start":
        return cmd_start(args)
    elif args.command == "stop":
        return cmd_stop(args)
    elif args.command == "status":
        return cmd_status(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
