"""Integration tests for state consistency.

Tests that state remains consistent across different access methods
and handles concurrent operations correctly.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from src.config import get_settings
from tests.integration.helpers import MockWebSocket


class TestStateConsistency:
    """Test suite for state consistency across different access methods."""
    
    @pytest.mark.asyncio
    async def test_state_consistency_webhook_vs_polling(
        self, test_client, reset_state, reset_connections
    ):
        """Test that webhook updates are visible via /current-state endpoint."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        # Initial state
        response = test_client.get("/current-state")
        initial_data = response.json()
        initial_timestamp = initial_data["last_update_time"]
        
        # Send webhook
        response = test_client.post(
            "/webhook/update",
            json={"page": 5, "y": 100},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # Poll for state
        response = test_client.get("/current-state")
        polled_data = response.json()
        
        # Verify consistency
        assert polled_data["page"] == 5
        assert polled_data["y"] == 100
        assert polled_data["last_update_time"] > initial_timestamp
        assert pdf_state.current_page == 5
        assert pdf_state.current_y == 100
    
    @pytest.mark.asyncio
    async def test_state_timestamp_updates_correctly(
        self, test_client, reset_state, reset_connections
    ):
        """Test that timestamp changes on each update."""
        from src.state import pdf_state
        
        timestamps = []
        
        for i in range(3):
            # Wait a bit to ensure different timestamps
            await asyncio.sleep(0.01)
            
            response = test_client.post(
                "/webhook/update",
                json={"page": i + 1, "y": i * 100},
                headers={"X-API-Key": get_settings().secret}
            )
            assert response.status_code == 200
            
            timestamps.append(pdf_state.last_update_time)
        
        # Verify timestamps are increasing
        assert timestamps[0] < timestamps[1] < timestamps[2]
    
    @pytest.mark.asyncio
    async def test_concurrent_webhook_updates(
        self, test_client, reset_state, reset_connections
    ):
        """Test race condition: multiple simultaneous webhooks."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        mock_ws = MockWebSocket()
        
        await manager.connect(mock_ws)
        
        # Send multiple webhooks concurrently
        async def send_webhook(page, y):
            return test_client.post(
                "/webhook/update",
                json={"page": page, "y": y},
                headers={"X-API-Key": get_settings().secret}
            )
        
        # Fire multiple concurrent requests
        tasks = [
            send_webhook(i, i * 50) for i in range(1, 6)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
        
        # State should have one of the values (last one wins)
        # We don't know which one due to race, but it should be consistent
        assert 1 <= pdf_state.current_page <= 5
        assert pdf_state.current_y is not None
        
        # All broadcasts should have been sent
        assert len(mock_ws.sent_messages) == 5
        
        # Cleanup
        manager.disconnect(mock_ws)
    
    @pytest.mark.asyncio
    async def test_state_persistence_across_connections(
        self, test_client, reset_state, reset_connections
    ):
        """Test that state persists when clients disconnect and reconnect."""
        from src.state import pdf_state
        from src.connection_manager import manager
        
        # First client connects
        client1 = MockWebSocket()
        
        await manager.connect(client1)
        
        # Update state
        response = test_client.post(
            "/webhook/update",
            json={"page": 3, "y": 200},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # First client disconnects
        manager.disconnect(client1)
        
        # Second client connects
        client2 = MockWebSocket()
        
        await manager.connect(client2)
        
        # State should still be the same
        assert pdf_state.current_page == 3
        assert pdf_state.current_y == 200
        
        # New client shouldn't receive old messages, but state is there
        assert len(client2.sent_messages) == 0  # No broadcast since connection
        
        # Verify via API
        response = test_client.get("/current-state")
        data = response.json()
        assert data["page"] == 3
        assert data["y"] == 200
        
        # Cleanup
        manager.disconnect(client2)
    
    @pytest.mark.asyncio
    async def test_state_read_during_update(
        self, test_client, reset_state, reset_connections
    ):
        """Test /current-state called while webhook is updating."""
        from src.state import pdf_state
        
        results = []
        
        async def read_state():
            response = test_client.get("/current-state")
            results.append(("read", response.json()))
        
        async def update_state(page):
            response = test_client.post(
                "/webhook/update",
                json={"page": page, "y": page * 100},
                headers={"X-API-Key": get_settings().secret}
            )
            results.append(("update", response.status_code))
        
        # Interleave reads and updates
        tasks = []
        for i in range(5):
            tasks.append(read_state())
            tasks.append(update_state(i + 1))
        tasks.append(read_state())
        
        await asyncio.gather(*tasks)
        
        # All operations should complete
        reads = [r for r in results if r[0] == "read"]
        updates = [r for r in results if r[0] == "update"]
        
        assert len(reads) == 6
        assert len(updates) == 5
        
        # All updates should succeed
        for _, status in updates:
            assert status == 200
    
    def test_state_types_are_consistent(
        self, test_client, reset_state
    ):
        """Test that state values have correct types."""
        # Update state
        response = test_client.post(
            "/webhook/update",
            json={"page": 5, "y": 100.5},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # Read state
        response = test_client.get("/current-state")
        data = response.json()
        
        # Verify types
        assert isinstance(data["page"], int)
        assert isinstance(data["y"], float)
        assert isinstance(data["last_update_time"], int)
