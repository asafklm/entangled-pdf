"""Configuration management for PdfServer.

Uses Pydantic Settings for type-safe configuration with environment variable support.
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support.
    
    Environment variables are prefixed with PDF_SERVER_.
    Example: PDF_SERVER_PORT=8080
    
    Attributes:
        pdf_file: Path to the PDF file to serve (required)
        port: Server port number (default: 8431)
        secret: API key for webhook authentication (default: super-secret-123)
        host: Server host address (default: 0.0.0.0)
        static_dir: Directory containing static files (default: static/)
    """
    
    model_config = SettingsConfigDict(
        env_prefix="PDF_SERVER_",
        case_sensitive=False,
        extra="ignore"  # Ignore extra env vars
    )
    
    pdf_file: Path
    port: int = 8431
    secret: str = "super-secret-123"
    host: str = "0.0.0.0"
    static_dir: Path = Path("static")
    
    def model_post_init(self, __context) -> None:
        """Validate settings after initialization."""
        # Ensure pdf_file is absolute path
        if not self.pdf_file.is_absolute():
            self.pdf_file = self.pdf_file.resolve()
        
        # Validate PDF file exists
        if not self.pdf_file.exists():
            raise ValueError(f"PDF file not found: {self.pdf_file}")
        
        # Validate static directory exists
        if not self.static_dir.exists():
            raise ValueError(f"Static directory not found: {self.static_dir}")


# Global settings instance (initialized in main.py)
settings: Optional[Settings] = None


def init_settings(pdf_file: Optional[Path] = None, port: Optional[int] = None) -> Settings:
    """Initialize global settings.
    
    Args:
        pdf_file: Override PDF file path (optional)
        port: Override port number (optional)
    
    Returns:
        Settings: Initialized settings instance
    """
    global settings
    
    kwargs = {}
    if pdf_file is not None:
        kwargs["pdf_file"] = Path(pdf_file)
    if port is not None:
        kwargs["port"] = port
    
    settings = Settings(**kwargs)
    return settings


def get_settings() -> Settings:
    """Get the global settings instance.
    
    Returns:
        Settings: The global settings instance
    
    Raises:
        RuntimeError: If settings have not been initialized
    """
    if settings is None:
        raise RuntimeError("Settings not initialized. Call init_settings() first.")
    return settings
