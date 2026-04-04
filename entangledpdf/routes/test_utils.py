"""Test utilities endpoint for E2E testing.

Provides endpoints to reset server state between tests.
Only enabled when ENTANGLEDPDF_TEST_MODE environment variable is set.
"""

import os

from fastapi import APIRouter, HTTPException

from entangledpdf.config import get_settings
from entangledpdf.state import PDFState, pdf_state

router = APIRouter()

TEST_MODE = os.getenv("ENTANGLEDPDF_TEST_MODE", "").lower() in ("1", "true", "yes")


@router.post("/api/test/reset", include_in_schema=TEST_MODE)
async def reset_state() -> dict:
    """Reset server state for testing.
    
    Clears the current PDF file and resets all state to defaults.
    Only available in test mode.
    
    Returns:
        dict: Success status
    """
    if not TEST_MODE:
        raise HTTPException(status_code=404, detail="Not found")
    
    global pdf_state
    pdf_state = PDFState()
    
    settings = get_settings()
    settings.pdf_file = None
    
    return {"status": "success", "message": "State reset"}
