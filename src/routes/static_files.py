"""Static files serving route.

Serves JavaScript, CSS, and other static assets.
"""

from fastapi.staticfiles import StaticFiles

from src.config import get_settings


def setup_static_files(app) -> None:
    """Configure static files serving.
    
    Mounts the static directory at /static URL path.
    
    Args:
        app: FastAPI application instance
    """
    settings = get_settings()
    app.mount(
        "/static",
        StaticFiles(directory=str(settings.static_dir)),
        name="static"
    )
