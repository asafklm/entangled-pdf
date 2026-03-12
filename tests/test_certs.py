"""Tests for SSL certificate handling in src.certs."""

from pathlib import Path

import pytest

from pdfserver import certs


def test_validate_certificate_not_found():
    missing = Path("/tmp/file-does-not-exist-for-tests.crt")
    info = certs.validate_certificate(missing)
    assert info["exists"] is False
    assert info["error"] is not None


def test_copy_existing_cert_not_found_raises():
    src_cert = Path("/tmp/nonexistent.crt")
    src_key = Path("/tmp/nonexistent.key")
    with pytest.raises(FileNotFoundError):
        certs.copy_existing_cert(src_cert, src_key)
