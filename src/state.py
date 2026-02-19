"""State management for PDF synchronization.

Tracks the current viewing position (page and y-coordinate) and provides
timestamp-based update tracking to prevent unnecessary scrolling.
"""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PDFState:
    """Tracks the current PDF viewing state.
    
    This class maintains the current page, vertical position, and timestamp
    of the last update. It's used to synchronize viewers across multiple
    devices and to detect new updates when a tab regains focus.
    
    Attributes:
        current_page: The currently viewed page number (1-indexed)
        current_y: The vertical position in PDF points (optional)
        last_update_time: Timestamp of last update in milliseconds
    """
    current_page: int = 1
    current_y: Optional[float] = None
    last_update_time: int = field(default_factory=lambda: int(time.time() * 1000))
    
    def update(self, page: int, y: Optional[float] = None) -> None:
        """Update the current state with new position.
        
        Args:
            page: New page number
            y: New vertical position (optional)
        """
        self.current_page = page
        self.current_y = y
        self.last_update_time = int(time.time() * 1000)
    
    def to_dict(self) -> dict:
        """Convert state to dictionary for JSON serialization.
        
        Returns:
            dict: Current state as a dictionary
        """
        return {
            "page": self.current_page,
            "y": self.current_y,
            "last_update_time": self.last_update_time
        }


# Singleton state instance
pdf_state = PDFState()
