"""Tests for configuration module."""

import os
from pathlib import Path

import pytest

from src.config import Settings, init_settings, get_settings


class TestSettings:
    """Test suite for Settings configuration."""
    
    def test_default_values(self, tmp_path):
        """Test default configuration values."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        settings = Settings(pdf_file=pdf_file)
        
        assert settings.port == 8431
        assert settings.secret == "super-secret-123"
        assert settings.host == "0.0.0.0"
    
    def test_custom_values(self, tmp_path):
        """Test custom configuration values."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        settings = Settings(
            pdf_file=pdf_file,
            port=8080,
            secret="custom-secret",
            host="127.0.0.1"
        )
        
        assert settings.port == 8080
        assert settings.secret == "custom-secret"
        assert settings.host == "127.0.0.1"
    
    def test_missing_pdf_file(self, tmp_path):
        """Test that missing PDF file raises error."""
        pdf_file = tmp_path / "nonexistent.pdf"
        
        with pytest.raises(ValueError, match="PDF file not found"):
            Settings(pdf_file=pdf_file)
    
    def test_env_prefix(self, tmp_path, monkeypatch):
        """Test environment variable prefix."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        monkeypatch.setenv("PDF_SERVER_PORT", "9090")
        monkeypatch.setenv("PDF_SERVER_SECRET", "env-secret")
        
        settings = Settings(pdf_file=pdf_file)
        
        assert settings.port == 9090
        assert settings.secret == "env-secret"


class TestSettingsGlobal:
    """Test suite for global settings functions."""
    
    def test_init_settings(self, tmp_path):
        """Test settings initialization."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        settings = init_settings(pdf_file=pdf_file, port=7000)
        
        assert settings.port == 7000
        assert settings.pdf_file == pdf_file
    
    def test_get_settings_without_init(self):
        """Test that get_settings raises error if not initialized."""
        # Reset global settings
        import src.config
        src.config.settings = None
        
        with pytest.raises(RuntimeError, match="Settings not initialized"):
            get_settings()
