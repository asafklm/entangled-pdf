"""Static files serving route.

Serves JavaScript, CSS, PDF.js library, and other static assets.
"""

from pathlib import Path

from fastapi.staticfiles import StaticFiles

from src.config import get_settings


def setup_static_files(app) -> None:
    """Configure static files serving.
    
    Mounts:
    - /static - Application static files (JS, CSS, templates)
    - /pdfjs - PDF.js library files from pdfjs-dist/build
    
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
    
    # Mount PDF.js library files (local copy for offline/air-gapped use)
    pdfjs_path = Path(__file__).parent.parent.parent / "pdfjs-dist" / "build"
    if pdfjs_path.exists():
        app.mount(
            "/pdfjs",
            StaticFiles(directory=str(pdfjs_path)),
            name="pdfjs"
        )
