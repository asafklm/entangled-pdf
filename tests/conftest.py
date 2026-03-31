"""Root pytest configuration for tests.

Provides fixtures that are shared across all test files.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set default API key for tests
os.environ.setdefault("PDF_SERVER_API_KEY", "test-api-key-for-testing")


@pytest.fixture(scope="function")
def real_test_client():
    """Create a test client using the real static directory.
    
    This fixture is for tests that need to verify the actual HTML template
    and static files, not the minimal test fixtures.
    """
    from main import create_app
    from pdfserver.config import Settings, settings as global_settings
    from pdfserver.state import pdf_state
    from pdfserver.connection_manager import manager
    
    project_root = Path(__file__).parent.parent
    static_dir = project_root / "static"
    
    if not static_dir.exists():
        pytest.skip("static directory not found")
    
    # Create a test PDF file
    test_pdf = project_root / "test_document.pdf"
    test_pdf.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n")
    
    # Create settings with real static directory
    settings = Settings(
        pdf_file=test_pdf,
        port=18080,
        api_key="test-api-key-for-testing",
        static_dir=static_dir
    )
    
    # Patch the global settings before creating the app
    with patch("pdfserver.config.settings", settings):
        app = create_app()
        
        with patch("pdfserver.routes.view.get_settings", return_value=settings):
            with patch("pdfserver.routes.pdf.get_settings", return_value=settings):
                with patch("pdfserver.routes.state.get_settings", return_value=settings):
                    with TestClient(app) as client:
                        yield client
    
    # Cleanup
    if test_pdf.exists():
        test_pdf.unlink()


# Import fixtures from integration tests
from tests.integration.conftest import (
    test_app,
    test_client,
    test_settings,
    temp_pdf_file,
    reset_state,
    reset_connections,
    mock_websocket_client,
)
