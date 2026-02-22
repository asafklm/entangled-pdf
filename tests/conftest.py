"""Root pytest configuration for tests.

Provides fixtures that are shared across all test files.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
