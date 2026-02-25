"""End-to-end integration tests for PdfServer.

Tests the complete user workflow from Neovim/VimTeX to browser rendering.
"""

import asyncio
import time

import pytest
from src.config import get_settings
from tests.integration.helpers import MockWebSocket


class TestEndToEndSyncTeX:
    """Test suite for end-to-end SyncTeX workflow."""
    
    @pytest.mark.asyncio
    async def test_full_synctex_workflow(
        self, test_client, reset_state, reset_connections
    ):
        """Simulate complete flow: Neovim → webhook → WebSocket → browser."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        # Step 1: Browser connects (simulated)
        browser = MockWebSocket()
        
        await manager.connect(browser)
        assert browser.accepted
        
        # Step 2: User edits in Neovim, SyncTeX triggers webhook
        # (Simulated by direct webhook call)
        response = test_client.post(
            "/webhook/update",
            json={"page": 5, "y": 250.5},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # Step 3: State updated
        assert pdf_state.current_page == 5
        assert pdf_state.current_y == 250.5
        
        # Step 4: Browser receives WebSocket message
        assert len(browser.sent_messages) == 1
        msg = browser.sent_messages[0]
        assert msg["page"] == 5
        assert msg["y"] == 250.5
        assert msg["action"] == "synctex"
        
        # Step 5: Browser would scroll (verified by message content)
        # In real browser, this triggers scrollToPage()
        
        # Cleanup
        manager.disconnect(browser)
    
    @pytest.mark.asyncio
    async def test_browser_reconnects_and_syncs(
        self, test_client, reset_state, reset_connections
    ):
        """Test browser disconnects, comes back, syncs to current position."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        # Initial browser connects
        browser1 = MockWebSocket()
        
        await manager.connect(browser1)
        
        # Updates happen while connected
        response = test_client.post(
            "/webhook/update",
            json={"page": 10, "y": 500},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # First browser receives update
        assert len(browser1.sent_messages) == 1
        
        # Browser disconnects (e.g., network issue, page refresh)
        manager.disconnect(browser1)
        
        # More updates happen while disconnected
        response = test_client.post(
            "/webhook/update",
            json={"page": 15, "y": 750},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # Browser reconnects
        browser2 = MockWebSocket()
        
        await manager.connect(browser2)
        
        # Browser polls for current state (simulating syncState())
        response = test_client.get("/state")
        current_state = response.json()
        
        # Browser syncs to current position
        assert current_state["page"] == 15
        assert current_state["y"] == 750
        assert current_state["last_update_time"] == pdf_state.last_update_time
        
        # New updates go to reconnected browser
        response = test_client.post(
            "/webhook/update",
            json={"page": 20, "y": 1000},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # Reconnected browser receives new update
        assert len(browser2.sent_messages) == 1
        assert browser2.sent_messages[0]["page"] == 20
        
        # Cleanup
        manager.disconnect(browser2)
    
    @pytest.mark.asyncio
    async def test_multiple_browsers_sync_together(
        self, test_client, reset_state, reset_connections
    ):
        """Test two browsers, one update, both sync."""
        from src.connection_manager import manager
        
        # Two browsers open same PDF
        browser1 = MockWebSocket()
        
        browser2 = MockWebSocket()
        
        await manager.connect(browser1)
        await manager.connect(browser2)
        
        # User edits in Neovim
        response = test_client.post(
            "/webhook/update",
            json={"page": 8, "y": 400},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # Both browsers receive same update
        assert len(browser1.sent_messages) == 1
        assert len(browser2.sent_messages) == 1
        
        assert browser1.sent_messages[0] == browser2.sent_messages[0]
        assert browser1.sent_messages[0]["page"] == 8
        assert browser1.sent_messages[0]["y"] == 400
        
        # Cleanup
        manager.disconnect(browser1)
        manager.disconnect(browser2)
    
    @pytest.mark.asyncio
    async def test_editing_session_with_multiple_updates(
        self, test_client, reset_state, reset_connections
    ):
        """Simulate a full editing session with multiple updates."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        # Browser and editor setup
        browser = MockWebSocket()
        
        await manager.connect(browser)
        
        # Simulate editing session
        edits = [
            {"page": 1, "y": 100},   # Introduction
            {"page": 3, "y": 200},   # Chapter 1
            {"page": 3, "y": 350},   # Chapter 1 continued
            {"page": 5, "y": 150},   # Chapter 2
            {"page": 7, "y": 400},   # Conclusion
        ]
        
        for edit in edits:
            # Neovim triggers SyncTeX
            response = test_client.post(
                "/webhook/update",
                json=edit,
                headers={"X-API-Key": get_settings().secret}
            )
            assert response.status_code == 200
            
            # Small delay between edits
            await asyncio.sleep(0.01)
        
        # Verify final state
        assert pdf_state.current_page == 7
        assert pdf_state.current_y == 400
        
        # All updates received by browser
        assert len(browser.sent_messages) == 5
        
        # Verify sequence
        for i, msg in enumerate(browser.sent_messages):
            assert msg["page"] == edits[i]["page"]
            assert msg["y"] == edits[i]["y"]
        
        # Cleanup
        manager.disconnect(browser)
    
    def test_pdf_served_to_browser(self, test_client, temp_pdf_file):
        """Test that PDF is served correctly to browser."""
        # Browser requests PDF
        response = test_client.get("/get-pdf")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 0
        
        # Verify it's valid PDF (starts with %PDF)
        assert response.content.startswith(b"%PDF")
    
    def test_viewer_html_served(self, test_client, temp_pdf_file):
        """Test that viewer HTML is served with correct config."""
        from src.config import get_settings
        
        settings = get_settings()
        
        response = test_client.get("/view")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Verify config is present
        html = response.text
        assert "PDF_CONFIG" in html
        assert str(settings.port) in html
        assert settings.pdf_file.name in html
    
    @pytest.mark.asyncio
    async def test_fallback_polling_when_websocket_fails(
        self, test_client, reset_state, reset_connections
    ):
        """Test browser falls back to polling when WebSocket fails."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        # No WebSocket connection (simulating failure)
        
        # Initial state check via polling
        response = test_client.get("/state")
        initial_data = response.json()
        initial_timestamp = initial_data["last_update_time"]
        
        # Update happens via webhook
        response = test_client.post(
            "/webhook/update",
            json={"page": 5, "y": 250},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # Browser polls and detects new state
        response = test_client.get("/state")
        polled_data = response.json()
        
        # Browser detects update via polling
        assert polled_data["last_update_time"] > initial_timestamp
        assert polled_data["page"] == 5
        assert polled_data["y"] == 250
