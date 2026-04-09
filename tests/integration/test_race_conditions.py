"""Integration tests for race conditions.

Tests synchronization issues in the PDF server, particularly around
refreshing and scrolling as mentioned by the user.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from entangledpdf.config import get_settings
from tests.integration.helpers import MockWebSocket


@pytest.mark.slow
class TestRaceConditions:
    """Test suite for race conditions in the PDF server."""
    
    @pytest.mark.asyncio
    async def test_rapid_updates_dont_cause_inconsistent_state(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test that 100 updates/sec don't cause inconsistent state."""
        from entangledpdf.state import pdf_state
        from entangledpdf.connection_manager import manager
        
        mock_ws = MockWebSocket()
        
        await manager.connect(mock_ws)
        
        # Rapid updates (100 updates) using synctex params
        start_time = time.time()
        
        async def send_update(line):
            response = test_client.post(
                "/webhook/update",
                json={"line": line, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
                headers={"X-API-Key": get_settings().api_key}
            )
            return response.status_code
        
        # Send 100 rapid updates (lines 1-100)
        tasks = [send_update(i) for i in range(1, 101)]
        results = await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        
        # All should succeed
        assert all(status == 200 for status in results)
        
        # State should be one of the updates (last one likely won)
        # Page = line//10 + 1, so range is roughly 1-10
        assert 1 <= pdf_state.current_page <= 10
        assert pdf_state.current_y is not None
        
        # Should have received all 100 broadcasts
        assert len(mock_ws.sent_messages) == 100
        
        # Cleanup
        manager.disconnect(mock_ws)
    
    @pytest.mark.asyncio
    async def test_broadcast_during_client_connection(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test broadcast sent while client is connecting."""
        from entangledpdf.connection_manager import manager
        
        # Start a connection process (but don't await it fully)
        mock_ws = MockWebSocket()
        
        async def slow_accept():
            await asyncio.sleep(0.05)  # Slow connection
            mock_ws.accepted = True
        
        mock_ws.accept = slow_accept
        
        # Start connecting
        connect_task = asyncio.create_task(manager.connect(mock_ws))
        
        # Immediately send a webhook while connection is in progress (line: 50)
        await asyncio.sleep(0.01)  # Tiny delay to ensure connection started
        
        response = test_client.post(
            "/webhook/update",
            json={"line": 50, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().api_key}
        )
        
        assert response.status_code == 200
        
        # Wait for connection to complete
        await connect_task
        
        # Depending on timing, client may or may not receive the message
        # But it shouldn't crash
        
        # Cleanup
        manager.disconnect(mock_ws)
    
    @pytest.mark.asyncio
    async def test_multiple_broadcasts_order_preserved(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test that sequential broadcasts arrive in order."""
        from entangledpdf.connection_manager import manager
        
        mock_ws = MockWebSocket()
        
        await manager.connect(mock_ws)
        
        # Send 10 sequential updates using synctex params
        # Lines 10, 20, 30, ... 100 -> pages 1, 2, 3, ... 10
        for i in range(10):
            line = (i + 1) * 10  # 10, 20, 30, ..., 100
            response = test_client.post(
                "/webhook/update",
                json={"line": line, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
                headers={"X-API-Key": get_settings().api_key}
            )
            assert response.status_code == 200
            await asyncio.sleep(0.001)  # Tiny delay to ensure order
        
        # Verify all messages received
        assert len(mock_ws.sent_messages) == 10
        
        # Verify order is preserved (page numbers should be 1-10)
        pages = [msg["page"] for msg in mock_ws.sent_messages]
        assert pages == list(range(1, 11))
        
        # Cleanup
        manager.disconnect(mock_ws)
    
    @pytest.mark.asyncio
    async def test_client_reconnect_race_condition(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test client reconnects during broadcast."""
        from entangledpdf.connection_manager import manager
        
        # Client 1 connects and disconnects
        client1 = MockWebSocket()
        
        await manager.connect(client1)
        
        # Simulate rapid disconnect/reconnect
        manager.disconnect(client1)
        
        # Immediately reconnect (before any broadcasts)
        client2 = MockWebSocket()
        
        await manager.connect(client2)
        
        # Now send broadcast (line: 30 -> page 3, y 300)
        response = test_client.post(
            "/webhook/update",
            json={"line": 30, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().api_key}
        )
        
        assert response.status_code == 200
        
        # New client should receive it
        assert len(client2.sent_messages) == 1
        assert client2.sent_messages[0]["page"] == 3
        
        # Old client shouldn't have received anything after disconnect
        # (it may have received earlier messages, but not this one)
        
        # Cleanup
        manager.disconnect(client2)
    
    @pytest.mark.asyncio
    async def test_simultaneous_client_connections(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test multiple clients connecting simultaneously."""
        from entangledpdf.connection_manager import manager
        
        # Create 10 clients that will connect simultaneously
        clients = []
        for i in range(10):
            client = MockWebSocket()
            clients.append(client)
        
        # Connect all clients simultaneously
        connect_tasks = [manager.connect(client) for client in clients]
        await asyncio.gather(*connect_tasks)
        
        # Send a broadcast (line: 50 -> page 5, y 500)
        response = test_client.post(
            "/webhook/update",
            json={"line": 50, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().api_key}
        )
        
        assert response.status_code == 200
        
        # All clients should receive it
        for client in clients:
            assert len(client.sent_messages) == 1
            assert client.sent_messages[0]["page"] == 5
        
        # Cleanup
        for client in clients:
            manager.disconnect(client)
    
    @pytest.mark.asyncio
    async def test_broadcast_with_failing_client(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test broadcast continues even if one client fails."""
        from entangledpdf.connection_manager import manager
        
        # Working client
        good_client = MockWebSocket()
        
        # Failing client
        bad_client = MockWebSocket(should_fail=True)
        
        # Connect both
        await manager.connect(good_client)
        await manager.connect(bad_client)
        
        # Send broadcast (should not crash) (line: 50 -> page 5, y 500)
        response = test_client.post(
            "/webhook/update",
            json={"line": 50, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
            headers={"X-API-Key": get_settings().api_key}
        )
        
        assert response.status_code == 200
        
        # Good client should receive
        assert len(good_client.sent_messages) == 1
        
        # Bad client should have failed
        assert bad_client.should_fail
        
        # Verify bad_client is no longer in active connections
        assert manager.get_connection_count() == 1
        
        # Cleanup
        manager.disconnect(good_client)
    
    @pytest.mark.asyncio
    async def test_concurrent_state_reads_and_writes(
        self, test_client, reset_state, reset_connections, mock_synctex
    ):
        """Test concurrent reads and writes to state."""
        from entangledpdf.state import pdf_state
        
        results = []
        
        async def writer_task(line):
            response = test_client.post(
                "/webhook/update",
                json={"line": line, "col": 0, "tex_file": "test.tex", "pdf_file": "test.pdf"},
                headers={"X-API-Key": get_settings().api_key}
            )
            results.append(("write", response.status_code, line))
        
        async def reader_task():
            response = test_client.get("/state")
            data = response.json()
            results.append(("read", data["page"], data["y"]))
        
        # Mix of reads and writes (use lines 10-200)
        tasks = []
        for i in range(20):
            if i % 3 == 0:
                tasks.append(reader_task())
            else:
                tasks.append(writer_task((i + 1) * 10))  # 10, 20, 30, ..., 200
        
        await asyncio.gather(*tasks)
        
        # All should complete without error
        writes = [r for r in results if r[0] == "write"]
        reads = [r for r in results if r[0] == "read"]
        
        # All writes should succeed
        for _, status, _ in writes:
            assert status == 200
        
        # Final state should be consistent
        assert pdf_state.current_page is not None
        assert isinstance(pdf_state.current_page, int)
