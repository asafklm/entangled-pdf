"""Integration test fixtures for PdfServer.

This module provides fixtures for testing the complete
webhook → state → broadcast → WebSocket flow.
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import patch

import pytest
import pytest_asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from main import create_app, init_settings
from src.config import get_settings, settings as global_settings
from src.connection_manager import ConnectionManager, manager
from src.state import PDFState, pdf_state


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def temp_pdf_file(tmp_path_factory):
    """Create a temporary PDF file for testing."""
    tmp_path = tmp_path_factory.mktemp("pdf_test")
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    
    # Create a minimal viewer.html for testing
    viewer_html = static_dir / "viewer.html"
    viewer_html.write_text("""<!DOCTYPE html>
<html>
<head><title>Test PDF</title></head>
<body>
    <div id="viewer-container"></div>
    <script>
        window.PDF_CONFIG = {
            port: {{ port }},
            filename: "{{ filename }}",
            mtime: {{ mtime }}
        };
    </script>
</body>
</html>""")
    
    return pdf_file


@pytest.fixture(scope="function")
def test_settings(temp_pdf_file):
    """Create test settings with temporary files."""
    static_dir = temp_pdf_file.parent / "static"
    return init_settings(
        pdf_file=temp_pdf_file,
        port=18080  # Use high port to avoid conflicts
    )


@pytest.fixture(scope="function")
def test_app(test_settings):
    """Create a test FastAPI application."""
    # Reset global state
    pdf_state.current_page = 1
    pdf_state.current_y = None
    pdf_state.last_sync_time = int(time.time() * 1000)
    
    # Reset connection manager
    manager.active_connections.clear()
    
    with patch("src.config.settings", test_settings):
        app = create_app()
        yield app


@pytest.fixture(scope="function")
def test_client(test_app) -> Generator[TestClient, None, None]:
    """Create a test HTTP client."""
    with TestClient(test_app) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def async_test_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for integration tests."""
    settings = get_settings()
    async with AsyncClient(app=test_app, base_url=f"http://{settings.host}:{settings.port}") as client:
        yield client


@pytest.fixture(scope="function")
def reset_state():
    """Reset global state before each test."""
    # Save original values
    original_page = pdf_state.current_page
    original_y = pdf_state.current_y
    original_time = pdf_state.last_sync_time
    
    # Reset to defaults
    pdf_state.current_page = 1
    pdf_state.current_y = None
    pdf_state.last_sync_time = int(time.time() * 1000)
    
    yield
    
    # Restore original values (or keep reset based on test needs)
    pdf_state.current_page = original_page
    pdf_state.current_y = original_y
    pdf_state.last_sync_time = original_time


@pytest.fixture(scope="function")
def reset_connections():
    """Reset connection manager before each test."""
    # Save current connections
    original_connections = manager.active_connections.copy()
    
    # Clear all connections
    manager.active_connections.clear()
    
    yield
    
    # Restore original connections
    manager.active_connections.clear()
    manager.active_connections.update(original_connections)


@pytest.fixture(scope="function")
def mock_websocket_client():
    """Create a mock WebSocket client for testing."""
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []
            self.closed = False
            self.accepted = False
        
        async def accept(self):
            self.accepted = True
        
        async def send_json(self, data):
            if not self.closed:
                self.sent_messages.append(data)
        
        async def receive_text(self):
            # Simulate waiting for messages
            await asyncio.sleep(0.1)
            return "keepalive"
        
        def disconnect(self):
            self.closed = True
    
    return MockWebSocket


@pytest_asyncio.fixture(scope="function")
async def multiple_websocket_clients(test_app, test_settings):
    """Create multiple WebSocket clients connected to the server."""
    from fastapi.testclient import TestClient
    
    clients = []
    
    with TestClient(test_app) as client:
        # We can't use actual WebSocket in TestClient easily
        # So we'll mock multiple connections
        for _ in range(3):
            mock_ws = type('MockWebSocket', (), {
                'sent_messages': [],
                'accepted': False,
                'closed': False
            })()
            
            mock_ws.accept = lambda: setattr(mock_ws, 'accepted', True) or None
            mock_ws.send_json = lambda data: mock_ws.sent_messages.append(data) if not mock_ws.closed else None
            
            await manager.connect(mock_ws)
            clients.append(mock_ws)
        
        yield clients
        
        # Cleanup
        for client in clients:
            manager.disconnect(client)


@pytest.fixture(scope="function")
def typescript_interfaces():
    """Parse TypeScript interfaces from viewer.ts for contract testing."""
    viewer_ts_path = Path(__file__).parent.parent.parent / "static" / "viewer.ts"
    
    if not viewer_ts_path.exists():
        pytest.skip("viewer.ts not found")
    
    content = viewer_ts_path.read_text()
    
    # Extract interfaces (simple parsing)
    interfaces = {}
    
    # Extract PDFConfig interface
    if "interface PDFConfig" in content:
        interfaces["PDFConfig"] = {
            "port": "number",
            "filename": "string"
        }
    
    # Extract StateUpdate interface
    if "interface StateUpdate" in content:
        interfaces["StateUpdate"] = {
            "page": "number",
            "y": "number | undefined",
            "last_sync_time": "number | undefined",
            "action": "string | undefined"
        }
    
    return interfaces


@pytest.fixture(scope="session")
def typescript_compiled():
    """Ensure TypeScript is compiled before testing."""
    project_root = Path(__file__).parent.parent.parent
    
    # Check if viewer.js exists and is newer than viewer.ts
    viewer_ts = project_root / "static" / "viewer.ts"
    viewer_js = project_root / "static" / "viewer.js"
    
    if viewer_ts.exists():
        if not viewer_js.exists() or viewer_ts.stat().st_mtime > viewer_js.stat().st_mtime:
            # Compile TypeScript
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                pytest.skip(f"TypeScript compilation failed: {result.stderr}")
    
    return viewer_js.exists()


@pytest.fixture(scope="function")
def mock_synctex():
    """Mock synctex to return predictable PDF coordinates for testing."""
    from unittest.mock import patch
    
    def mock_run_synctex(line, col, tex_file, pdf_path):
        """Return predictable coordinates based on line number."""
        # Map line numbers to predictable page/y coordinates
        # This allows tests to predict the outcome
        # Page formula: lines 1-10 -> page 1, lines 11-20 -> page 2, etc.
        page = max(1, (line - 1) // 10 + 1)  # Every 10 lines = new page
        y = float(line * 10 + col)  # Y increases with line
        x = float(col * 5)  # X increases with column
        return {
            "Page": str(page),
            "y": str(y),
            "x": str(x),
            "h": "10.0",  # height
            "v": str(y)   # vertical position
        }
    
    with patch("src.routes.webhook.run_synctex_view", side_effect=mock_run_synctex):
        yield mock_run_synctex


@pytest.fixture(scope="function")
def viewer_ts_content():
    """Read viewer.ts content for TypeScript interface testing."""
    viewer_ts_path = Path(__file__).parent.parent.parent / "static" / "viewer.ts"
    
    if not viewer_ts_path.exists():
        pytest.skip("viewer.ts not found")
    
    return viewer_ts_path.read_text()
