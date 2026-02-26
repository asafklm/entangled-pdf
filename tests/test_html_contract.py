"""HTML Template Contract Tests for PdfServer.

Tests that verify the HTML template structure and loading order
to prevent race conditions and DOM access errors.

These tests catch issues like:
- Scripts loading before required DOM elements exist
- Incorrect script execution order
- Missing required configuration data
- Wrong script attributes (defer, async, type)
"""

import re

import pytest
from fastapi.testclient import TestClient


class TestScriptLoadingOrder:
    """Tests to verify correct script loading order."""
    
    def test_pdf_config_script_before_viewer_js(self, test_client: TestClient):
        """Verify PDF_CONFIG is defined before viewer.js loads.
        
        This prevents the race condition where viewer.js tries to access
        window.PDF_CONFIG before it's defined by the inline script.
        """
        response = test_client.get("/view")
        assert response.status_code == 200
        
        html = response.text
        
        # Find positions of both scripts
        pdf_config_pos = html.find("window.PDF_CONFIG")
        # Match viewer.js with optional query parameters (cache-busting)
        viewer_js_match = re.search(r'src="/static/viewer\.js[^"]*"', html)
        viewer_js_pos = viewer_js_match.start() if viewer_js_match else -1
        
        assert pdf_config_pos != -1, (
            "PDF_CONFIG must be defined in HTML. "
            "Required by viewer.js for configuration."
        )
        
        assert viewer_js_pos != -1, (
            "viewer.js script tag must be present in HTML"
        )
        
        assert pdf_config_pos < viewer_js_pos, (
            "PDF_CONFIG must be defined BEFORE viewer.js loads.\n"
            f"PDF_CONFIG at position {pdf_config_pos}, "
            f"viewer.js at position {viewer_js_pos}\n"
            "Move the inline PDF_CONFIG script before the viewer.js script tag."
        )
    
    def test_no_defer_or_async_on_module_scripts(self, test_client: TestClient):
        """Verify viewer.js doesn't have defer/async attributes that could cause race conditions.
        
        ES modules load asynchronously by default, adding defer/async can cause
        timing issues with module initialization.
        """
        response = test_client.get("/view")
        assert response.status_code == 200
        
        html = response.text
        
        # Find the viewer.js script tag (with optional cache-busting query params)
        script_pattern = r'<script[^>]*src="/static/viewer\.js[^"]*"[^>]*>'
        matches = re.findall(script_pattern, html, re.IGNORECASE)
        
        assert len(matches) > 0, "viewer.js script tag must be present"
        
        for match in matches:
            assert 'defer' not in match.lower(), (
                f"viewer.js should not have defer attribute: {match}\n"
                "ES modules already load asynchronously. "
                "defer can cause timing issues."
            )
            
            assert 'async' not in match.lower(), (
                f"viewer.js should not have async attribute: {match}\n"
                "ES modules already load asynchronously. "
                "async can cause timing issues."
            )
    
    def test_required_dom_elements_before_scripts(self, test_client: TestClient):
        """Verify required DOM elements exist before JavaScript runs.
        
        viewer.js accesses these elements immediately on load:
        - #viewer-container (required for PDF rendering)
        - #status (optional, but should exist)
        """
        response = test_client.get("/view")
        assert response.status_code == 200
        
        html = response.text
        
        # Find element positions
        container_pos = html.find('id="viewer-container"')
        # Match viewer.js with optional query parameters (cache-busting)
        viewer_js_match = re.search(r'src="/static/viewer\.js[^"]*"', html)
        viewer_js_pos = viewer_js_match.start() if viewer_js_match else -1
        
        assert container_pos != -1, (
            "viewer-container element must exist in HTML. "
            "Required by viewer.js for PDF rendering."
        )
        
        assert container_pos < viewer_js_pos, (
            "viewer-container must be defined BEFORE viewer.js loads.\n"
            "viewer.js accesses document.getElementById('viewer-container') immediately.\n"
            f"Container at position {container_pos}, viewer.js at position {viewer_js_pos}"
        )


class TestModuleScriptValidation:
    """Tests to verify correct ES module usage in HTML."""
    
    def test_viewer_js_is_es_module(self, test_client: TestClient):
        """Verify viewer.js is loaded as ES module (type='module').
        
        This is critical for the import * as pdfjsLib from '/pdfjs/pdf.mjs' 
        statement to work correctly. Without type='module', the import
        statement will cause a syntax error.
        """
        response = test_client.get("/view")
        assert response.status_code == 200
        
        html = response.text
        
        # Find the viewer.js script tag (with optional cache-busting query params)
        script_pattern = r'<script[^>]*src="/static/viewer\.js[^"]*"[^>]*>'
        matches = re.findall(script_pattern, html, re.IGNORECASE)
        
        assert len(matches) > 0, "viewer.js script tag must be present"
        
        for match in matches:
            assert 'type="module"' in match or "type='module'" in match, (
                f"viewer.js must be loaded as ES module: {match}\n"
                "Add type='module' attribute.\n"
                "Without this, the ES module import in viewer.js will fail."
            )
    
    def test_no_redundant_pdfjs_import_in_html(self, test_client: TestClient):
        """Verify HTML doesn't have redundant pdfjsLib import.
        
        viewer.js now imports pdfjsLib directly, so having a separate
        inline script that also imports it is redundant and can cause
        confusion about which import is being used.
        """
        response = test_client.get("/view")
        assert response.status_code == 200
        
        html = response.text
        
        # Count pdfjsLib imports (should only be in viewer.js)
        import_count = html.count("import * as pdfjsLib")
        
        # Remove the viewer.js reference to count only inline scripts (with optional query params)
        viewer_js_pattern = r'<script[^>]*src="/static/viewer\.js[^"]*"[^>]*>.*?</script>'
        html_without_viewer_js = re.sub(
            viewer_js_pattern, 
            '', 
            html, 
            flags=re.DOTALL | re.IGNORECASE
        )
        
        inline_import_count = html_without_viewer_js.count("import * as pdfjsLib")
        
        assert inline_import_count == 0, (
            f"HTML should not have inline pdfjsLib import.\n"
            f"Found {inline_import_count} inline import(s) of pdfjsLib.\n"
            "viewer.js imports pdfjsLib directly - no need for inline import.\n"
            "Remove any inline <script type='module'> that imports pdfjsLib."
        )


class TestConfigurationDataValidation:
    """Tests to verify configuration data is properly embedded."""
    
    def test_pdf_config_has_required_fields(self, test_client: TestClient):
        """Verify PDF_CONFIG contains all required fields.
        
        Required fields:
        - port: number (WebSocket port)
        - filename: string (PDF filename for display)
        """
        response = test_client.get("/view")
        assert response.status_code == 200
        
        html = response.text
        
        # Extract PDF_CONFIG object
        config_match = re.search(
            r'window\.PDF_CONFIG\s*=\s*\{([^}]+)\}',
            html,
            re.DOTALL
        )
        
        assert config_match is not None, (
            "window.PDF_CONFIG must be defined in HTML\n"
            "Expected pattern: window.PDF_CONFIG = { port: ..., filename: ... }"
        )
        
        config_content = config_match.group(1)
        
        # Check required fields
        assert 'port' in config_content, (
            "PDF_CONFIG must have 'port' field\n"
            "Required for WebSocket connection"
        )
        
        assert 'filename' in config_content, (
            "PDF_CONFIG must have 'filename' field\n"
            "Required for page title and display"
        )
    
    def test_pdf_config_values_are_valid(self, test_client: TestClient):
        """Verify PDF_CONFIG values are valid types and ranges.
        
        - port: positive integer
        - filename: non-empty string
        """
        response = test_client.get("/view")
        assert response.status_code == 200
        
        html = response.text
        
        # Extract port value
        port_match = re.search(r'port:\s*(\d+)', html)
        assert port_match is not None, "PDF_CONFIG port must be a number"
        
        port = int(port_match.group(1))
        assert 1 <= port <= 65535, (
            f"PDF_CONFIG port must be valid port number (1-65535), got {port}"
        )
        
        # Extract filename value
        filename_match = re.search(r'filename:\s*"([^"]+)"', html)
        assert filename_match is not None, (
            "PDF_CONFIG filename must be a string\n"
            "Expected pattern: filename: \"example.pdf\""
        )
        
        filename = filename_match.group(1)
        assert len(filename) > 0, "PDF_CONFIG filename must not be empty"
        assert filename.endswith('.pdf'), (
            f"PDF_CONFIG filename should end with .pdf, got: {filename}"
        )


class TestHTMLStructureValidation:
    """Tests to verify overall HTML structure."""
    
    def test_html_has_doctype(self, test_client: TestClient):
        """Verify HTML has proper DOCTYPE declaration."""
        response = test_client.get("/view")
        assert response.status_code == 200
        
        html = response.text
        
        assert html.strip().startswith('<!DOCTYPE html>'), (
            "HTML must start with <!DOCTYPE html>\n"
            "Required for standards mode rendering"
        )
    
    def test_html_has_viewport_meta(self, test_client: TestClient):
        """Verify HTML has viewport meta tag for mobile compatibility."""
        response = test_client.get("/view")
        assert response.status_code == 200
        
        html = response.text
        
        assert '<meta name="viewport"' in html.lower(), (
            "HTML must have viewport meta tag\n"
            "Required for mobile device compatibility\n"
            'Expected: <meta name="viewport" content="width=device-width, initial-scale=1.0">'
        )
    
    def test_title_is_set(self, test_client: TestClient):
        """Verify HTML has title tag set from filename."""
        response = test_client.get("/view")
        assert response.status_code == 200
        
        html = response.text
        
        title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
        assert title_match is not None, "HTML must have <title> tag"
        
        title = title_match.group(1)
        assert len(title) > 0, "Title must not be empty"
        assert '.pdf' in title.lower(), (
            f"Title should contain PDF filename, got: {title}"
        )
