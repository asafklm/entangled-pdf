"""CLI entry point for entangle-pdf command.

This module provides the main entry point for the entangle-pdf CLI tool,
which manages the PDF server lifecycle.
"""

import argparse
import os
import re
import socket
import subprocess
import sys
from pathlib import Path
from typing import Optional

import argcomplete
import secrets

from entangledpdf.socket_path import get_socket_path, is_server_running
from entangledpdf.sync import (
    load_pdf,
    forward_search,
    parse_synctex_forward,
    get_server_state,
    get_default_socket_path
)

# Configuration
DEFAULT_PORT = 8431


def get_network_info() -> dict:
    """Get all relevant network addresses for URL display."""
    info = {'hostname': socket.gethostname()}
    
    try:
        result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
        current_iface = None
        for line in result.stdout.split('\n'):
            if ': ' in line and not line.startswith(' '):
                current_iface = line.split(':')[1].strip().split()[0]
            
            match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', line)
            if match:
                ip = match.group(1)
                if ip != '127.0.0.1':
                    if current_iface:
                        if 'tailscale' in current_iface:
                            info['tailscale'] = ip
                        elif 'docker' in current_iface:
                            info['docker'] = ip
                        elif any(x in current_iface for x in ['eth', 'ens', 'enp']):
                            info['primary'] = ip
    except Exception:
        pass
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        info['outbound'] = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    
    return info


def format_status_urls(port: int, use_https: bool) -> list:
    """Format URLs for status display."""
    info = get_network_info()
    protocol = 'https' if use_https else 'http'
    urls = []
    seen = set()
    
    for key in ['tailscale', 'docker', 'primary', 'outbound']:
        if key in info and info[key] not in seen:
            seen.add(info[key])
            label = {'tailscale': 'remote (Tailscale)', 'docker': 'remote (Docker)', 
                     'primary': 'remote', 'outbound': 'remote'}[key]
            urls.append((f'{protocol}://{info[key]}:{port}/view', label))
    
    if 'hostname' in info and info['hostname']:
        try:
            resolved = socket.gethostbyname(info['hostname'])
            if resolved != '127.0.1.1' and resolved not in seen:
                seen.add(resolved)
                urls.append((f"{protocol}://{info['hostname']}:{port}/view", 'if DNS resolves'))
        except socket.gaierror:
            pass
    
    urls.append((f'{protocol}://localhost:{port}/view', 'local only'))
    return urls


def get_server_dir() -> Path:
    """Get the server directory (parent of package)."""
    import entangledpdf
    
    package_dir = Path(entangledpdf.__file__).parent.resolve()
    server_dir = package_dir.parent
    return server_dir


def get_python_cmd() -> str:
    """Get Python command to use."""
    return sys.executable


def cmd_start(args):
    """Start the PDF server (foreground mode)."""
    port = args.port or int(os.getenv("ENTANGLEDPDF_PORT", DEFAULT_PORT))
    socket_path = args.socket_path or get_socket_path()
    
    # Check if server already running via socket
    if is_server_running(socket_path):
        print(f"Error: Server already running", file=sys.stderr)
        print(f"Socket: {socket_path}", file=sys.stderr)
        print(f"Press Ctrl+C to stop the running server", file=sys.stderr)
        return 1
    
    # Find the main.py file
    try:
        import entangledpdf
        package_dir = Path(entangledpdf.__file__).parent
        main_py = package_dir.parent / "main.py"
        
        if not main_py.exists():
            main_py = package_dir.parent / "main.py"
        
        if not main_py.exists():
            main_py = Path.cwd() / "main.py"
            
        if not main_py.exists():
            print("Error: Could not find main.py.", file=sys.stderr)
            print("If you installed via pip/pipx, run 'python main.py' from the project directory.", file=sys.stderr)
            print("For development, use: pip install -e .", file=sys.stderr)
            return 1
    except ImportError:
        print("Error: Could not import entangledpdf package", file=sys.stderr)
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
        escaped_cmd = args.inverse_search_command.replace("%", "%%")
        cmd.extend(["--inverse-search-command", escaped_cmd])
    elif args.inverse_search_nvim:
        cmd.append("--inverse-search-nvim")
    elif args.inverse_search_emacs:
        cmd.append("--inverse-search-emacs")
    elif args.inverse_search_vim:
        cmd.append("--inverse-search-vim")
    
    if args.verbose:
        cmd.append("--verbose")
    
    if args.log_file:
        cmd.extend(["--log-file", str(args.log_file)])
    
    if args.api_key:
        cmd.extend(["--api-key", args.api_key])
    
    if args.ssl_cert:
        cmd.extend(["--ssl-cert", str(args.ssl_cert)])
    
    if args.ssl_key:
        cmd.extend(["--ssl-key", str(args.ssl_key)])
    
    # Set environment
    env = os.environ.copy()
    env["ENTANGLEDPDF_PORT"] = str(port)
    
    # Run server in foreground - this will block until Ctrl+C
    print(f"Starting EntangledPdf on port {port}...")
    print(f"Unix socket: {socket_path}")
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


def cmd_status(args):
    """Show server status via Unix socket."""
    socket_path = args.socket_path or get_default_socket_path()
    
    state = get_server_state(socket_path)
    
    if state is None:
        print(f"Server not running (socket: {socket_path})")
        return 0
    
    # Show status
    print(f"Server running")
    print(f"  Status: {'Ready' if state.get('pdf_loaded') else 'Waiting for PDF'}")
    print(f"  PDF: {state.get('pdf_file', 'None')}")
    print(f"  Socket: {socket_path}")
    
    if state.get('pdf_mtime'):
        import datetime
        mtime = datetime.datetime.fromtimestamp(state['pdf_mtime'])
        print(f"  PDF modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Display authentication token if available
    if state.get('websocket_token'):
        print(f"\n  Authentication Token (for browser access): {state['websocket_token']}")
        print(f"    ↑ This token is only needed when accessing the PDF viewer via browser.")
        print(f"      CLI commands on this machine use Unix socket authentication instead.")
    
    # Display browser URLs
    port = state.get('port', DEFAULT_PORT)
    use_https = state.get('https', True)
    urls = format_status_urls(port, use_https)
    print("\n  Open the following URL in your browser and enter the authentication token:")
    for url, label in urls:
        print(f"    {url}  ({label})")
    
    return 0


def cmd_sync(args):
    """Load PDF and optionally perform forward search via Unix socket."""
    socket_path = args.socket_path or get_default_socket_path()
    
    try:
        # Load PDF
        if args.verbose:
            print(f"Loading PDF: {args.pdf_file}")
        
        response = load_pdf(args.pdf_file, socket_path)
        
        if args.verbose:
            print(f"Loaded: {response.get('filename', args.pdf_file.name)}")
        
        # Perform forward search if synctex info provided
        if args.synctex:
            line, column, tex_file = parse_synctex_forward(args.synctex)
            
            # Resolve tex_file to absolute path and validate it exists
            tex_file_path = Path(tex_file).resolve()
            if not tex_file_path.exists():
                raise FileNotFoundError(f"TeX source file not found: {tex_file_path}")
            
            if args.verbose:
                print(f"Forward search: line={line}, column={column}, file={tex_file_path}")
            
            search_response = forward_search(
                line,
                column,
                str(tex_file_path),
                str(args.pdf_file),
                socket_path
            )
            
            if args.verbose:
                page = search_response.get('page')
                x = search_response.get('x')
                y = search_response.get('y')
                if page and x is not None and y is not None:
                    print(f"Forward: line {line} → page {page} @ (x={x:.2f}, y={y:.2f})")
                else:
                    print(f"Forward search: no position found")
        
        print(f"PDF loaded successfully: {response.get('pdf_file', args.pdf_file)}")
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        if "socket" in str(e).lower():
            print("Is the server running? Use: entangle-pdf start", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_generate_api_key(args) -> int:
    """Generate a secure API key for authentication.
    
    Note: API keys are only required for browser access. The CLI commands
    (sync, status) use Unix socket authentication instead.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    api_key = secrets.token_hex(32)
    
    if args.shell:
        print(f'export ENTANGLEDPDF_API_KEY="{api_key}"')
        print("# Add the above line to your ~/.bashrc or ~/.zshrc", file=sys.stderr)
        print("# Then run: source ~/.bashrc", file=sys.stderr)
        print("# Note: API keys are only needed for browser access", file=sys.stderr)
    else:
        print(api_key)
    
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="EntangledPdf management tool (foreground mode only)",
        prog="entangle-pdf"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # start command
    start_parser = subparsers.add_parser("start", help="Start the PDF server (foreground)")
    
    start_parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("ENTANGLEDPDF_PORT", DEFAULT_PORT)),
        help=f"Server port (default: {DEFAULT_PORT} or ENTANGLEDPDF_PORT env var)"
    )
    
    start_parser.add_argument(
        "--socket-path",
        type=Path,
        default=None,
        help="Path to Unix socket (default: $XDG_RUNTIME_DIR/entangledpdf/server.sock)"
    )
    
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
        "--inverse-search-emacs",
        action="store_true",
        help="Enable inverse search for Emacs (uses emacsclient)"
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
        help="API key for authentication (default: ENTANGLEDPDF_API_KEY env var)"
    )
    
    start_parser.add_argument(
        "--ssl-cert",
        metavar="PATH",
        type=Path,
        help="Path to SSL certificate file (PEM format)"
    )
    
    start_parser.add_argument(
        "--ssl-key",
        metavar="PATH",
        type=Path,
        help="Path to SSL private key file (PEM format)"
    )
    
    # status command
    status_parser = subparsers.add_parser("status", help="Show server status")
    
    status_parser.add_argument(
        "--socket-path",
        type=Path,
        default=None,
        help="Path to Unix socket (default: $XDG_RUNTIME_DIR/entangledpdf/server.sock)"
    )
    
    # generate-api-key command
    key_parser = subparsers.add_parser("generate-api-key", help="Generate a secure API key")
    key_parser.add_argument(
        "--shell",
        action="store_true",
        help="Output in shell export format for easy sourcing"
    )
    
    # sync command
    sync_parser = subparsers.add_parser("sync", help="Load PDF and perform forward search")
    
    sync_parser.add_argument(
        "pdf_file",
        type=Path,
        help="Path to PDF file to load"
    )
    
    sync_parser.add_argument(
        "synctex",
        nargs="?",
        metavar="LINE:COL:FILE",
        help="Optional forward search in format line:column:texfile"
    )
    
    sync_parser.add_argument(
        "--socket-path",
        type=Path,
        default=None,
        help="Path to Unix socket (default: $XDG_RUNTIME_DIR/entangledpdf/server.sock)"
    )
    
    sync_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Enable bash completion
    argcomplete.autocomplete(parser)
    
    args = parser.parse_args()
    
    if args.command == "start":
        return cmd_start(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "sync":
        return cmd_sync(args)
    elif args.command == "generate-api-key":
        return cmd_generate_api_key(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
