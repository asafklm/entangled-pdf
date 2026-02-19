"""PDF serving route.

Serves the PDF file with proper content type and security headers.
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from src.config import get_settings

router = APIRouter()


@router.get("/get-pdf")
async def get_pdf() -> FileResponse:
    """Serve the PDF file.
    
    Returns the configured PDF file with proper Content-Type header.
    The file path is validated during settings initialization.
    
    Returns:
        FileResponse: The PDF file with application/pdf content type
    """
    settings = get_settings()
    
    return FileResponse(
        settings.pdf_file,
        media_type="application/pdf",
        filename=settings.pdf_file.name
    )
