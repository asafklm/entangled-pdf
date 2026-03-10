"""Comprehensive tests for src.logging_sanitizer.SensitiveDataFilter."""

import logging

from src.logging_sanitizer import SensitiveDataFilter


def test_filter_redacts_token_and_password_in_dict():
    f = SensitiveDataFilter()
    logger = logging.getLogger("test")
    logger.addFilter(f)
    
    args = {"token": "secret-token", "password": "pwd"}
    rec = logger.makeRecord("test", logging.INFO, __file__, 1, "test message", (args,), None)
    f.filter(rec)
    
    assert isinstance(rec.args, dict)
    assert rec.args.get("token") == "[REDACTED]"
    assert rec.args.get("password") == "[REDACTED]"


def test_filter_redacts_nested_password():
    f = SensitiveDataFilter()
    logger = logging.getLogger("test_nested")
    logger.addFilter(f)
    
    args = {"nested": {"password": "hidden"}}
    rec = logger.makeRecord("test_nested", logging.INFO, __file__, 1, "test message", (args,), None)
    f.filter(rec)
    
    assert isinstance(rec.args, dict)
    nested = rec.args.get("nested")
    assert isinstance(nested, dict)
    assert nested.get("password") == "[REDACTED]"


def test_filter_sanitizes_strings_with_patterns():
    f = SensitiveDataFilter()
    logger = logging.getLogger("test_url")
    logger.addFilter(f)
    
    args = {"url": "http://user:pass@example.com"}
    rec = logger.makeRecord("test_url", logging.INFO, __file__, 1, "test message", (args,), None)
    f.filter(rec)
    
    assert isinstance(rec.args, dict)
    assert "***REDACTED***" in rec.args.get("url", "")


def test_filter_redacts_api_key():
    f = SensitiveDataFilter()
    logger = logging.getLogger("test_api")
    logger.addFilter(f)
    
    args = {"api_key": "sk-1234567890"}
    rec = logger.makeRecord("test_api", logging.INFO, __file__, 1, "test message", (args,), None)
    f.filter(rec)
    
    assert isinstance(rec.args, dict)
    assert rec.args.get("api_key") == "[REDACTED]"


def test_filter_preserves_non_sensitive_data():
    f = SensitiveDataFilter()
    logger = logging.getLogger("test_preserve")
    logger.addFilter(f)
    
    args = {"username": "john", "action": "login", "count": 42}
    rec = logger.makeRecord("test_preserve", logging.INFO, __file__, 1, "test message", (args,), None)
    f.filter(rec)
    
    assert isinstance(rec.args, dict)
    assert rec.args.get("username") == "john"
    assert rec.args.get("action") == "login"
    assert rec.args.get("count") == 42
