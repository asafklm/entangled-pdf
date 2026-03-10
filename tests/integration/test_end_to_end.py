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
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Simulate complete flow: Neovim → webhook → WebSocket → browser."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        # Step 1: Browser connects (simulated)
        browser = MockWebSocket()
        
        await manager.connect(browser)
        assert browser.accepted
        
        # Step 2: User edits in Neovim, SyncTeX triggers webhook
        # Send webhook with synctex params (line: 42, col: 5 -> page 5, y 425)
        response = test_client.post(
            "/webhook/update",
            json={"line": 42, "col": 5, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # Step 3: State updated (line 42 -> page 5, y 425)
        assert pdf_state.current_page == 5
        assert pdf_state.current_y == 425.0
        
        # Step 4: Browser receives WebSocket message
        assert len(browser.sent_messages) == 1
        msg = browser.sent_messages[0]
        assert msg["page"] == 5
        assert msg["y"] == 425.0
        assert msg["action"] == "synctex"
        
        # Step 5: Browser would scroll (verified by message content)
        # In real browser, this triggers scrollToPage()
        
        # Cleanup
        manager.disconnect(browser)
    
    @pytest.mark.asyncio
    async def test_browser_reconnects_and_syncs(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test browser disconnects, comes back, syncs to current position."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        # Initial browser connects
        browser1 = MockWebSocket()
        
        await manager.connect(browser1)
        
        # Updates happen while connected (line: 100 -> page 10, y 1000)
        response = test_client.post(
            "/webhook/update",
            json={"line": 100, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # First browser receives update
        assert len(browser1.sent_messages) == 1
        
        # Browser disconnects (e.g., network issue, page refresh)
        manager.disconnect(browser1)
        
        # More updates happen while disconnected (line: 150 -> page 15, y 1500)
        response = test_client.post(
            "/webhook/update",
            json={"line": 150, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
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
        assert current_state["y"] == 1500.0
        assert current_state["last_sync_time"] == pdf_state.last_sync_time
        
        # New updates go to reconnected browser (line: 200 -> page 20, y 2000)
        response = test_client.post(
            "/webhook/update",
            json={"line": 200, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
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
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test two browsers, one update, both sync."""
        from src.connection_manager import manager
        
        # Two browsers open same PDF
        browser1 = MockWebSocket()
        
        browser2 = MockWebSocket()
        
        await manager.connect(browser1)
        await manager.connect(browser2)
        
        # User edits in Neovim (line: 80 -> page 8, y 800)
        response = test_client.post(
            "/webhook/update",
            json={"line": 80, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # Both browsers receive same update
        assert len(browser1.sent_messages) == 1
        assert len(browser2.sent_messages) == 1
        
        assert browser1.sent_messages[0] == browser2.sent_messages[0]
        assert browser1.sent_messages[0]["page"] == 8
        assert browser1.sent_messages[0]["y"] == 800.0
        
        # Cleanup
        manager.disconnect(browser1)
        manager.disconnect(browser2)
    
    @pytest.mark.asyncio
    async def test_editing_session_with_multiple_updates(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Simulate a full editing session with multiple updates."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        # Browser and editor setup
        browser = MockWebSocket()
        
        await manager.connect(browser)
        
        # Simulate editing session with synctex params
        # Line numbers map to pages: (line-1)//10 + 1
        edits = [
            {"line": 10, "col": 0},   # Introduction -> page 1, y 100
            {"line": 25, "col": 0},   # Chapter 1 -> page 3, y 250
            {"line": 30, "col": 0},   # Chapter 1 continued -> page 3, y 300
            {"line": 50, "col": 0},   # Chapter 2 -> page 5, y 500
            {"line": 70, "col": 0},   # Conclusion -> page 7, y 700
        ]
        
        for edit in edits:
            # Neovim triggers SyncTeX
            response = test_client.post(
                "/webhook/update",
                json={**edit, "tex_file": "test.tex", "pdf_file": "test.pdf"},
                headers={"X-API-Key": get_settings().secret}
            )
            assert response.status_code == 200
            
            # Small delay between edits
            await asyncio.sleep(0.01)
        
        # Verify final state (last edit: line 70 -> page 7, y 700)
        assert pdf_state.current_page == 7
        assert pdf_state.current_y == 700.0
        
        # All updates received by browser
        assert len(browser.sent_messages) == 5
        
        # Verify sequence
        expected_pages = [1, 3, 3, 5, 7]
        expected_ys = [100.0, 250.0, 300.0, 500.0, 700.0]
        for i, msg in enumerate(browser.sent_messages):
            assert msg["page"] == expected_pages[i]
            assert msg["y"] == expected_ys[i]
        
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
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test browser falls back to polling when WebSocket fails."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        # No WebSocket connection (simulating failure)
        
        # Initial state check via polling
        response = test_client.get("/state")
        initial_data = response.json()
        initial_timestamp = initial_data["last_sync_time"]
        
        # Update happens via webhook (line: 42 -> page 5, y 420)
        response = test_client.post(
            "/webhook/update",
            json={"line": 42, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # Browser polls and detects new state
        response = test_client.get("/state")
        polled_data = response.json()
        
        # Browser detects update via polling
        assert polled_data["last_sync_time"] > initial_timestamp
        assert polled_data["page"] == 5
        assert polled_data["y"] == 420.0
