"""Tests for configuration module."""

import os
from pathlib import Path

import pytest

from entangledpdf.config import Settings, init_settings, get_settings, ConfigError


class TestSettings:
    """Test suite for Settings configuration."""
    
    def test_default_values(self, tmp_path):
        """Test default configuration values with API key."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        settings = Settings(pdf_file=pdf_file, api_key="test-api-key")
        
        assert settings.port == 8431
        assert settings.api_key == "test-api-key"
        assert settings.host == "0.0.0.0"
    
    def test_custom_values(self, tmp_path):
        """Test custom configuration values."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        settings = Settings(
            pdf_file=pdf_file,
            port=8080,
            api_key="custom-secret",
            host="127.0.0.1"
        )
        
        assert settings.port == 8080
        assert settings.api_key == "custom-secret"
        assert settings.host == "127.0.0.1"
    
    def test_missing_api_key(self, tmp_path):
        """Test that missing API key raises ConfigError in init_settings."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        # Ensure env var is not set
        import os
        os.environ.pop("PDF_SERVER_API_KEY", None)
        
        with pytest.raises(ConfigError, match="API key is required"):
            init_settings(pdf_file=pdf_file)
    
    def test_missing_pdf_file(self, tmp_path):
        """Test that missing PDF file raises error."""
        pdf_file = tmp_path / "nonexistent.pdf"
        
        with pytest.raises(ValueError, match="PDF file not found"):
            Settings(pdf_file=pdf_file, api_key="test-key")
    
    def test_env_prefix(self, tmp_path, monkeypatch):
        """Test environment variable prefix."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        monkeypatch.setenv("PDF_SERVER_PORT", "9090")
        monkeypatch.setenv("PDF_SERVER_API_KEY", "env-secret")
        
        settings = Settings(pdf_file=pdf_file)
        
        assert settings.port == 9090
        assert settings.api_key == "env-secret"
    
    def test_api_key_from_env_var_only(self, tmp_path, monkeypatch):
        """Test that API key can be set via environment variable only."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        monkeypatch.setenv("PDF_SERVER_API_KEY", "env-api-key")
        
        settings = init_settings(pdf_file=pdf_file)
        
        assert settings.api_key == "env-api-key"


class TestSettingsGlobal:
    """Test suite for global settings functions."""
    
    def test_init_settings(self, tmp_path):
        """Test settings initialization."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        settings = init_settings(pdf_file=pdf_file, port=7000, api_key="test-key")
        
        assert settings.port == 7000
        assert settings.pdf_file == pdf_file
        assert settings.api_key == "test-key"
    
    def test_init_settings_without_api_key(self, tmp_path):
        """Test that init_settings requires API key."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        with pytest.raises(ConfigError, match="API key is required"):
            init_settings(pdf_file=pdf_file, port=7000)
    
    def test_get_settings_without_init(self):
        """Test that get_settings raises error if not initialized."""
        # Reset global settings
        import entangledpdf.config
        entangledpdf.config.settings = None
        
        with pytest.raises(RuntimeError, match="Settings not initialized"):
            get_settings()


class TestApiKeyValidation:
    """Test suite for API key validation behavior."""
    
    def test_server_fails_without_api_key_env_var(self, tmp_path):
        """Test that server fails to start without API key configuration."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        # Ensure env var is not set
        os.environ.pop("PDF_SERVER_API_KEY", None)
        
        with pytest.raises(ConfigError, match="API key is required"):
            init_settings(pdf_file=pdf_file)
    
    def test_server_accepts_api_key_via_argument(self, tmp_path):
        """Test that server accepts API key via constructor argument."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        # Don't set env var, pass directly
        os.environ.pop("PDF_SERVER_API_KEY", None)
        
        settings = Settings(pdf_file=pdf_file, api_key="arg-api-key")
        assert settings.api_key == "arg-api-key"
    
    def test_empty_api_key_fails(self, tmp_path):
        """Test that empty API key is rejected."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("dummy pdf content")
        
        with pytest.raises(ConfigError, match="API key is required"):
            init_settings(pdf_file=pdf_file, api_key="")
