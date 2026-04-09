"""Integration tests for the /api/load-pdf endpoint.

Tests dynamic PDF loading without server restart, including:
- Successful PDF loading
- Authentication and validation
- WebSocket broadcast to clients
- State updates
"""

import pytest
import pytest_asyncio
from pathlib import Path

from entangledpdf.config import get_settings
from entangledpdf.state import pdf_state
from entangledpdf.connection_manager import manager
from tests.integration.helpers import MockWebSocket


@pytest.mark.slow
class TestLoadPdfEndpoint:
    """Test the /api/load-pdf endpoint for dynamic PDF loading."""

    @pytest.mark.asyncio
    async def test_load_pdf_success(
        self, test_client, reset_state, reset_connections, temp_pdf_file
    ):
        """Test successfully loading a PDF via the API."""
        # Create mock WebSocket client
        mock_ws = MockWebSocket()
        await manager.connect(mock_ws)

        # Ensure no PDF is loaded initially
        settings = get_settings()
        original_pdf = settings.pdf_file

        try:
            # Load PDF via API
            response = test_client.post(
                "/api/load-pdf",
                json={"pdf_path": str(temp_pdf_file)},
                headers={"X-API-Key": get_settings().api_key}
            )

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
            assert result["changed"] is True
            assert result["filename"] == temp_pdf_file.name

            # Verify settings were updated
            assert settings.pdf_file == temp_pdf_file

            # Verify state was updated
            assert pdf_state.pdf_file == temp_pdf_file
            assert pdf_state.current_page == 1  # Reset to page 1
            assert pdf_state.pdf_mtime is not None

            # Verify broadcast was sent to WebSocket clients
            assert len(mock_ws.sent_messages) == 1
            broadcast = mock_ws.sent_messages[0]
            assert broadcast["action"] == "reload"
            assert "pdf_mtime" in broadcast
            assert broadcast["pdf_mtime"] == pdf_state.pdf_mtime

        finally:
            # Cleanup
            manager.disconnect(mock_ws)
            settings.pdf_file = original_pdf

    @pytest.mark.asyncio
    async def test_load_pdf_authentication_failure(
        self, test_client, reset_state, temp_pdf_file
    ):
        """Test that loading PDF fails with invalid API key."""
        response = test_client.post(
            "/api/load-pdf",
            json={"pdf_path": str(temp_pdf_file)},
            headers={"X-API-Key": "invalid-key"}
        )

        assert response.status_code == 403
        assert "Authentication failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_load_pdf_missing_path(
        self, test_client, reset_state
    ):
        """Test that loading PDF fails when pdf_path is missing."""
        response = test_client.post(
            "/api/load-pdf",
            json={},
            headers={"X-API-Key": get_settings().api_key}
        )

        assert response.status_code == 400
        assert "pdf_path" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_load_pdf_nonexistent_file(
        self, test_client, reset_state
    ):
        """Test that loading PDF fails when file doesn't exist."""
        response = test_client.post(
            "/api/load-pdf",
            json={"pdf_path": "/nonexistent/path/file.pdf"},
            headers={"X-API-Key": get_settings().api_key}
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_load_pdf_relative_path(
        self, test_client, reset_state, reset_connections, temp_pdf_file
    ):
        """Test that relative paths are resolved correctly.
        
        Note: Relative paths are resolved from CWD, so we use the absolute path
        of the temp file's parent directory to construct a relative path that works.
        """
        mock_ws = MockWebSocket()
        await manager.connect(mock_ws)

        settings = get_settings()
        original_pdf = settings.pdf_file

        try:
            # Create a relative path from CWD to the temp file
            # This simulates what entangle-pdf sync would do
            import os
            rel_path = os.path.relpath(temp_pdf_file, os.getcwd())

            response = test_client.post(
                "/api/load-pdf",
                json={"pdf_path": rel_path},
                headers={"X-API-Key": get_settings().api_key}
            )

            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"

            # Verify path was resolved to absolute
            assert settings.pdf_file.is_absolute()
            assert settings.pdf_file == temp_pdf_file

        finally:
            manager.disconnect(mock_ws)
            settings.pdf_file = original_pdf

    @pytest.mark.asyncio
    async def test_load_pdf_multiple_clients_broadcast(
        self, test_client, reset_state, reset_connections, temp_pdf_file
    ):
        """Test that all connected WebSocket clients receive the reload broadcast."""
        # Create multiple mock WebSocket clients
        mock_clients = [MockWebSocket() for _ in range(3)]

        for client in mock_clients:
            await manager.connect(client)

        settings = get_settings()
        original_pdf = settings.pdf_file

        try:
            # Load PDF via API
            response = test_client.post(
                "/api/load-pdf",
                json={"pdf_path": str(temp_pdf_file)},
                headers={"X-API-Key": get_settings().api_key}
            )

            assert response.status_code == 200

            # Verify all clients received the broadcast
            for client in mock_clients:
                assert len(client.sent_messages) == 1
                broadcast = client.sent_messages[0]
                assert broadcast["action"] == "reload"
                assert "pdf_mtime" in broadcast

        finally:
            for client in mock_clients:
                manager.disconnect(client)
            settings.pdf_file = original_pdf


@pytest.mark.slow
class TestLoadPdfStateUpdates:
    """Test state updates when loading PDFs dynamically."""

    @pytest.mark.asyncio
    async def test_load_pdf_updates_pdf_mtime(
        self, test_client, reset_state, reset_connections, temp_pdf_file
    ):
        """Test that loading PDF updates the pdf_mtime in state."""
        mock_ws = MockWebSocket()
        await manager.connect(mock_ws)

        settings = get_settings()
        original_pdf = settings.pdf_file

        try:
            # Get file mtime before loading
            expected_mtime = temp_pdf_file.stat().st_mtime

            response = test_client.post(
                "/api/load-pdf",
                json={"pdf_path": str(temp_pdf_file)},
                headers={"X-API-Key": get_settings().api_key}
            )

            assert response.status_code == 200

            # Verify state has correct mtime
            assert pdf_state.pdf_mtime == expected_mtime

            # Verify broadcast has correct mtime
            assert len(mock_ws.sent_messages) == 1
            broadcast = mock_ws.sent_messages[0]
            assert broadcast["pdf_mtime"] == expected_mtime

        finally:
            manager.disconnect(mock_ws)
            settings.pdf_file = original_pdf

    @pytest.mark.asyncio
    async def test_load_pdf_resets_to_page_one(
        self, test_client, reset_state, reset_connections, temp_pdf_file
    ):
        """Test that loading PDF resets view to page 1."""
        mock_ws = MockWebSocket()
        await manager.connect(mock_ws)

        settings = get_settings()
        original_pdf = settings.pdf_file

        try:
            # First set state to a different page
            pdf_state.update(5, 500.0)
            assert pdf_state.current_page == 5

            # Load PDF via API
            response = test_client.post(
                "/api/load-pdf",
                json={"pdf_path": str(temp_pdf_file)},
                headers={"X-API-Key": get_settings().api_key}
            )

            assert response.status_code == 200

            # Verify state was reset to page 1
            assert pdf_state.current_page == 1
            assert pdf_state.current_y is None

        finally:
            manager.disconnect(mock_ws)
            settings.pdf_file = original_pdf

    @pytest.mark.asyncio
    async def test_state_endpoint_returns_loaded_pdf(
        self, test_client, reset_state, reset_connections, temp_pdf_file
    ):
        """Test that /state endpoint returns correct info after dynamic load."""
        mock_ws = MockWebSocket()
        await manager.connect(mock_ws)

        settings = get_settings()
        original_pdf = settings.pdf_file

        try:
            # Load PDF via API
            response = test_client.post(
                "/api/load-pdf",
                json={"pdf_path": str(temp_pdf_file)},
                headers={"X-API-Key": get_settings().api_key}
            )

            assert response.status_code == 200

            # Check state endpoint
            state_response = test_client.get("/state")
            assert state_response.status_code == 200

            state_data = state_response.json()
            assert state_data["pdf_loaded"] is True
            assert state_data["pdf_file"] == str(temp_pdf_file)
            assert state_data["pdf_mtime"] == pdf_state.pdf_mtime
            assert state_data["page"] == 1

        finally:
            manager.disconnect(mock_ws)
            settings.pdf_file = original_pdf


@pytest.mark.slow
class TestLoadPdfSequential:
    """Test loading multiple PDFs sequentially."""

    @pytest.mark.asyncio
    async def test_load_multiple_pdfs_sequentially(
        self, test_client, reset_state, reset_connections, temp_pdf_file, test_settings
    ):
        """Test loading multiple different PDFs one after another."""
        # Create a second temporary PDF by copying and modifying the first
        # Use absolute path for the second PDF
        second_pdf = Path.cwd() / test_settings.static_dir / "second.pdf"
        
        # Copy the first PDF to create a second one
        import shutil
        shutil.copy(temp_pdf_file, second_pdf)
        
        # Touch it to update mtime to make it different
        import time
        time.sleep(0.1)
        second_pdf.touch()

        mock_ws = MockWebSocket()
        await manager.connect(mock_ws)

        settings = get_settings()
        original_pdf = settings.pdf_file

        try:
            # Load first PDF
            response1 = test_client.post(
                "/api/load-pdf",
                json={"pdf_path": str(temp_pdf_file)},
                headers={"X-API-Key": get_settings().api_key}
            )
            assert response1.status_code == 200

            first_mtime = pdf_state.pdf_mtime
            first_file = settings.pdf_file

            # Load second PDF
            response2 = test_client.post(
                "/api/load-pdf",
                json={"pdf_path": str(second_pdf)},
                headers={"X-API-Key": get_settings().api_key}
            )
            assert response2.status_code == 200

            # Verify state updated to second PDF
            assert settings.pdf_file == second_pdf
            assert pdf_state.pdf_file == second_pdf
            assert pdf_state.pdf_mtime != first_mtime

            # Verify both reload broadcasts were sent
            assert len(mock_ws.sent_messages) == 2
            for broadcast in mock_ws.sent_messages:
                assert broadcast["action"] == "reload"
                assert "pdf_mtime" in broadcast

        finally:
            manager.disconnect(mock_ws)
            settings.pdf_file = original_pdf
            if second_pdf.exists():
                second_pdf.unlink()
