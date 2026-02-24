"""Integration tests for URL redirect and cache-busting features.

Tests the flow: root URL → redirect → view with pdf param, and
cache-busting via mtime query parameter.
"""

import pytest
from pathlib import Path


class TestUrlRedirect:
    """Test suite for URL redirect flow."""
    
    def test_root_redirects_to_view_with_pdf_param(
        self, test_client, temp_pdf_file
    ):
        """Test that root URL redirects to /view with pdf query param."""
        response = test_client.get("/", follow_redirects=False)
        
        assert response.status_code == 307
        redirect_url = response.headers["location"]
        assert "/view" in redirect_url
        assert f"pdf={temp_pdf_file.name}" in redirect_url
    
    def test_view_page_contains_pdf_param_in_title(
        self, test_client, temp_pdf_file
    ):
        """Test that /view?pdf=... shows correct title."""
        response = test_client.get(f"/view?pdf={temp_pdf_file.name}")
        
        assert response.status_code == 200
        assert temp_pdf_file.name in response.text
    
    def test_view_page_contains_mtime(
        self, test_client, temp_pdf_file
    ):
        """Test that view response includes mtime in config."""
        response = test_client.get(f"/view?pdf={temp_pdf_file.name}")
        
        assert response.status_code == 200
        mtime = int(temp_pdf_file.stat().st_mtime)
        assert str(mtime) in response.text


class TestCacheBusting:
    """Test suite for cache-busting via mtime."""
    
    def test_pdf_endpoint_has_cache_headers(
        self, test_client
    ):
        """Test PDF endpoint returns caching headers."""
        response = test_client.get("/get-pdf")
        
        assert response.status_code == 200
        assert "Cache-Control" in response.headers
        assert "ETag" in response.headers
    
    def test_etag_is_based_on_file_mtime(
        self, test_client, temp_pdf_file
    ):
        """Test ETag value matches file mtime."""
        response = test_client.get("/get-pdf")
        
        mtime = int(temp_pdf_file.stat().st_mtime)
        expected_etag = f'"{mtime}"'
        
        assert response.headers["ETag"] == expected_etag
    
    def test_pdf_url_with_mtime_param(
        self, test_client, temp_pdf_file
    ):
        """Test that frontend would construct correct PDF URL with mtime."""
        mtime = int(temp_pdf_file.stat().st_mtime)
        
        # This is the URL the frontend should construct
        pdf_url = f"/get-pdf?v={mtime}"
        
        response = test_client.get(pdf_url)
        assert response.status_code == 200
