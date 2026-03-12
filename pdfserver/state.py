"""State management for PDF synchronization.

Tracks the current viewing position (page and y-coordinate), PDF file path,
and file modification time to detect changes and provide
timestamp-based update tracking to prevent unnecessary scrolling.
"""

import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def generate_websocket_token() -> str:
    """Generate a cryptographically secure random token for WebSocket authentication."""
    return secrets.token_urlsafe(32)


@dataclass
class PDFState:
    """Tracks the current PDF viewing state.
    
    This class maintains the current page, vertical position, timestamp
    of the last update, and PDF file information. It's used to synchronize 
    viewers across multiple devices and to detect new updates when a tab regains focus.
    
    Attributes:
        current_page: The currently viewed page number (1-indexed)
        current_y: The vertical position in PDF points (optional)
        current_x: The horizontal position for sync marker (optional)
        last_sync_time: Timestamp of last forward sync (synctex) in milliseconds
        pdf_file: Path to the currently loaded PDF file (optional)
        pdf_mtime: Last modification time of the PDF file (optional)
    """
    current_page: int = 1
    current_y: Optional[float] = None
    current_x: Optional[float] = None
    last_sync_time: int = field(default_factory=lambda: int(time.time() * 1000))
    pdf_file: Optional[Path] = None
    pdf_mtime: Optional[float] = None
    websocket_token: Optional[str] = field(default_factory=generate_websocket_token)
    inverse_search_enabled: bool = False
    inverse_search_command: Optional[str] = None
    
    def update(self, page: int, y: Optional[float] = None, x: Optional[float] = None) -> None:
        """Update the current state with new position.
        
        Args:
            page: New page number
            y: New vertical position (optional)
            x: New horizontal position for sync marker (optional)
        """
        self.current_page = page
        self.current_y = y
        self.current_x = x
        self.last_sync_time = int(time.time() * 1000)
    
    def update_pdf(self, pdf_path: Path) -> bool:
        """Update the PDF file path and check if file changed.
        
        Args:
            pdf_path: Path to the new PDF file
        
        Returns:
            bool: True if the PDF file changed (different path or mtime), False otherwise
        """
        try:
            new_mtime = pdf_path.stat().st_mtime
        except (OSError, FileNotFoundError):
            new_mtime = None
        
        # Check if PDF changed (different path or different mtime)
        path_changed = self.pdf_file != pdf_path
        mtime_changed = self.pdf_mtime != new_mtime
        
        # Update stored values
        self.pdf_file = pdf_path
        self.pdf_mtime = new_mtime
        
        return path_changed or mtime_changed
    
    def to_dict(self) -> dict:
        """Convert state to dictionary for JSON serialization.
        
        Returns:
            dict: Current state as a dictionary
        """
        return {
            "page": self.current_page,
            "y": self.current_y,
            "x": self.current_x,
            "last_sync_time": self.last_sync_time,
            "pdf_file": str(self.pdf_file) if self.pdf_file else None,
            "pdf_mtime": self.pdf_mtime,
            "pdf_loaded": self.pdf_file is not None
        }


# Singleton state instance
pdf_state = PDFState()
