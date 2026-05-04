"""Socket filesystem path management for Unix domain socket.

Provides path resolution based on XDG conventions and stale socket detection.
"""

import os
import socket
from pathlib import Path


def get_socket_path() -> Path:
    """Get the Unix socket path for server communication.
    
    Resolution order:
    1. $ENTANGLEDPDF_SOCKET environment variable
    2. $XDG_RUNTIME_DIR/entangledpdf/server.sock
    3. $HOME/.local/run/entangledpdf/server.sock
    
    Returns:
        Path to the Unix socket file
    """
    # Check environment variable first
    env_path = os.getenv("ENTANGLEDPDF_SOCKET")
    if env_path:
        return Path(env_path)
    
    # Try XDG_RUNTIME_DIR (preferred - typically /run/user/<uid>)
    xdg_runtime = os.getenv("XDG_RUNTIME_DIR")
    if xdg_runtime:
        return Path(xdg_runtime) / "entangledpdf" / "server.sock"
    
    # Fallback to home directory
    home = Path.home()
    return home / ".local" / "run" / "entangledpdf" / "server.sock"


def ensure_socket_directory(socket_path: Path) -> None:
    """Create socket parent directory with proper permissions.
    
    Creates the directory with mode 0700 (only owner can read/write).
    
    Args:
        socket_path: Path to the socket file
    """
    parent = socket_path.parent
    if not parent.exists():
        parent.mkdir(parents=True, mode=0o700)


def is_server_running(socket_path: Path) -> bool:
    """Check if a server is actually listening on the socket.
    
    Attempts to connect to the socket. Returns True if connection succeeds,
    False if connection is refused or socket doesn't exist.
    
    Args:
        socket_path: Path to the socket file
        
    Returns:
        True if server is running, False otherwise
    """
    if not socket_path.exists():
        return False
    
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(str(socket_path))
        sock.close()
        return True
    except (ConnectionRefusedError, FileNotFoundError):
        return False
    except Exception:
        return False


def remove_stale_socket(socket_path: Path) -> bool:
    """Remove a stale socket file if the server is not running.
    
    Args:
        socket_path: Path to the socket file
        
    Returns:
        True if socket was removed, False if it didn't exist or server is running
    """
    if not socket_path.exists():
        return False
    
    if is_server_running(socket_path):
        return False
    
    try:
        socket_path.unlink()
        return True
    except OSError:
        return False


def prepare_socket_path(socket_path: Path) -> None:
    """Prepare socket path for server startup.
    
    Creates parent directory and removes stale sockets.
    Raises RuntimeError if a server is already running.
    
    Args:
        socket_path: Path to the socket file
        
    Raises:
        RuntimeError: If a server is already running on this socket
    """
    # Ensure directory exists
    ensure_socket_directory(socket_path)
    
    # Check if server is already running
    if is_server_running(socket_path):
        raise RuntimeError(
            f"Server already running (socket: {socket_path}). "
            f"Use Ctrl+C to stop the existing server first."
        )
    
    # Remove stale socket if present
    remove_stale_socket(socket_path)
