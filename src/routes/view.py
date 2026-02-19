"""View route for serving the PDF viewer HTML page.

Uses Jinja2 templating for proper HTML rendering with variable substitution.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config import get_settings

router = APIRouter()

# Templates initialized lazily to avoid circular import issues
_templates = None


def get_templates() -> Jinja2Templates:
    """Get or create Jinja2 templates instance.
    
    Lazy initialization avoids circular import issues where routes
    are imported before settings are initialized.
    
    Returns:
        Jinja2Templates: Configured templates instance
    """
    global _templates
    if _templates is None:
        settings = get_settings()
        _templates = Jinja2Templates(directory=str(settings.static_dir))
    return _templates


@router.get("/view", response_class=HTMLResponse)
async def view_page(request: Request) -> HTMLResponse:
    """Serve the PDF viewer HTML page.
    
    Renders the viewer template with the current configuration:
    - Port number for WebSocket connection
    - PDF filename for display
    
    Args:
        request: The FastAPI request object
    
    Returns:
        HTMLResponse: Rendered HTML viewer page
    """
    settings = get_settings()
    templates = get_templates()
    
    return templates.TemplateResponse(
        request,
        "viewer.html",
        {
            "port": settings.port,
            "filename": settings.pdf_file.name
        }
    )
