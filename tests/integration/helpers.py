"""Helper functions for integration tests."""

import asyncio
from typing import Any, Dict, List, Optional


class MockWebSocket:
    """Mock WebSocket client for integration testing."""
    
    def __init__(self, should_fail: bool = False):
        self.sent_messages: List[Dict[str, Any]] = []
        self.accepted: bool = False
        self.closed: bool = False
        self.should_fail: bool = should_fail
    
    async def accept(self) -> None:
        """Accept the WebSocket connection."""
        self.accepted = True
    
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Send JSON data to the client."""
        if self.should_fail:
            raise Exception("Connection failed")
        if not self.closed:
            self.sent_messages.append(data)
    
    async def receive_text(self) -> str:
        """Receive text from the client."""
        await asyncio.sleep(0.1)
        return "keepalive"
    
    def disconnect(self) -> None:
        """Disconnect the client."""
        self.closed = True


def create_mock_websocket(should_fail: bool = False) -> MockWebSocket:
    """Create a properly configured mock WebSocket client.
    
    Args:
        should_fail: If True, send_json will raise an exception
        
    Returns:
        MockWebSocket: A mock WebSocket client ready for testing
    """
    return MockWebSocket(should_fail=should_fail)
