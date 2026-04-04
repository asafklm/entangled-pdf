"""PDF serving route.

Serves the PDF file with proper content type and security headers.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from entangledpdf.config import get_settings

router = APIRouter()


@router.get("/get-pdf")
async def get_pdf() -> FileResponse:
    """Serve the PDF file.
    
    Returns the configured PDF file with proper Content-Type header.
    Returns 404 if no PDF is currently loaded.
    
    Returns:
        FileResponse: The PDF file with application/pdf content type
    
    Raises:
        HTTPException: 404 if no PDF is loaded
    """
    settings = get_settings()
    
    # Check if a PDF is loaded
    if settings.pdf_file is None:
        raise HTTPException(status_code=404, detail="No PDF loaded")
    
    return FileResponse(
        settings.pdf_file,
        media_type="application/pdf",
        filename=settings.pdf_file.name,
        headers={
            "Cache-Control": "public, max-age=31536000"
        }
    )
