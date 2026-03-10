"""WebSocket traffic monitoring for PdfServer.

Logs all WebSocket messages in a concise one-line format.
Enabled via --monitor=ws command line flag.

Usage:
    python main.py --monitor=ws

Output format:
    [2024-01-15 14:23:01.234] [RECV] action=ping
    [2024-01-15 14:23:01.235] [SENT] action=pong
    [2024-01-15 14:23:05.456] [RECV] action=inverse_search page=3 x=120.5 y=350.2
    [2024-01-15 14:23:05.789] [SENT] action=synctex page=3 x=100.5 y=200.0
"""

import re
import sys
from datetime import datetime
from typing import Any, Optional, Set, TextIO


SANITIZED_KEYS: Set[str] = {"token", "password", "secret", "api_key", "x-api-key", "authorization", "credentials"}

BLOCKED_PATTERNS = [
    re.compile(r"://[^:]+:[^@]+@"),
    re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
]

ALLOWED_FIELDS: Set[str] = {"action", "page", "x", "y", "timestamp", "pdf_loaded", "pdf_file", "pdf_mtime", "last_sync_time", "message"}


class WebSocketMonitor:
    """Monitors and logs WebSocket message traffic.
    
    This is a singleton-style class that can be enabled/disabled at runtime.
    When disabled, all logging methods become no-ops for zero overhead.
    
    Attributes:
        enabled: Whether monitoring is currently active
        output: File-like object to write logs to (default: sys.stdout)
    
    Example:
        >>> monitor = WebSocketMonitor()
        >>> monitor.enable()
        >>> monitor.log_receive({"action": "ping"})
        [2024-01-15 14:23:01.234] [RECV] action=ping
    """
    
    def __init__(self, output: Optional[TextIO] = None) -> None:
        """Initialize the monitor.
        
        Args:
            output: File-like object to write logs to (default: sys.stdout)
        """
        self._enabled = False
        self.output = output or sys.stdout
    
    @property
    def enabled(self) -> bool:
        """Check if monitoring is enabled."""
        return self._enabled
    
    def enable(self) -> None:
        """Enable WebSocket monitoring."""
        self._enabled = True
    
    def disable(self) -> None:
        """Disable WebSocket monitoring."""
        self._enabled = False

    def _sanitize(self, message: dict[str, Any]) -> dict[str, Any]:
        """Sanitize message by removing sensitive data and limiting to allowed fields."""
        sanitized: dict[str, Any] = {}
        for key, value in message.items():
            key_lower = key.lower()

            if key_lower in SANITIZED_KEYS:
                sanitized[key] = "[REDACTED]"
                continue

            if isinstance(value, str):
                for pattern in BLOCKED_PATTERNS:
                    if pattern.search(value):
                        sanitized[key] = "[REDACTED]"
                        break
                else:
                    sanitized[key] = value
            else:
                sanitized[key] = value

        return {k: v for k, v in sanitized.items() if k in ALLOWED_FIELDS}

    def _format_message(self, message: dict) -> str:
        """Format message dict as concise key=value pairs.
        
        Args:
            message: The message dictionary to format
            
        Returns:
            Formatted string like "action=synctex page=3 x=100.5"
        """
        parts = []
        for key, value in sorted(message.items()):
            if isinstance(value, float):
                # Format floats with reasonable precision
                parts.append(f"{key}={value:.2f}")
            else:
                parts.append(f"{key}={value}")
        return " ".join(parts)
    
    def _log(self, direction: str, message: dict) -> None:
        """Internal method to log a message.

        Args:
            direction: Either "RECV" or "SENT"
            message: The message dictionary to log
        """
        if not self._enabled:
            return

        sanitized = self._sanitize(message)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        formatted = self._format_message(sanitized)
        
        try:
            self.output.write(f"[{timestamp}] [{direction}] {formatted}\n")
            self.output.flush()
        except Exception:
            # Silently ignore write errors to avoid disrupting server operation
            pass
    
    def log_receive(self, message: dict) -> None:
        """Log incoming message from client.
        
        Args:
            message: The received message dictionary
            
        Example output:
            [2024-01-15 14:23:01.234] [RECV] action=inverse_search page=3 x=120.50 y=350.20
        """
        self._log("RECV", message)
    
    def log_sent(self, message: dict) -> None:
        """Log outgoing message sent to client(s).
        
        Note: This logs messages sent via broadcast or direct send.
        For broadcasts, one log line represents the message sent to all clients.
        
        Args:
            message: The sent message dictionary
            
        Example output:
            [2024-01-15 14:23:05.789] [SENT] action=synctex page=3 x=100.50 y=200.00
        """
        self._log("SENT", message)


# Global singleton instance
monitor = WebSocketMonitor()
