"""Static files serving route.

Serves JavaScript, CSS, PDF.js library, favicon, and other static assets.
"""

from pathlib import Path

from fastapi import Response
from fastapi.staticfiles import StaticFiles

from entangledpdf.config import get_settings


def setup_static_files(app) -> None:
    """Configure static files serving.
    
    Mounts:
    - /static - Application static files (JS, CSS, templates, favicon)
    - /pdfjs - PDF.js library files from node_modules/pdfjs-dist/build
    - /favicon.ico - Shortcut to favicon for browser auto-requests
    
    Args:
        app: FastAPI application instance
    """
    settings = get_settings()
    
    # Mount application static files
    app.mount(
        "/static",
        StaticFiles(directory=str(settings.static_dir)),
        name="static"
    )
    
    # Serve favicon.ico at root for browser auto-requests
    favicon_path = settings.static_dir / "favicon.ico"
    if favicon_path.exists():
        @app.get("/favicon.ico", include_in_schema=False)
        async def favicon():
            return Response(
                content=favicon_path.read_bytes(),
                media_type="image/x-icon"
            )
    
    # Mount PDF.js library files from node_modules (installed via npm)
    pdfjs_path = Path(__file__).parent.parent.parent / "node_modules" / "pdfjs-dist" / "build"
    if pdfjs_path.exists():
        app.mount(
            "/pdfjs",
            StaticFiles(directory=str(pdfjs_path)),
            name="pdfjs"
        )
