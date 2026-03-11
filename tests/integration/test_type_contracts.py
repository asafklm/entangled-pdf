"""Integration tests for TypeScript interface contracts.

Tests that TypeScript type definitions match actual runtime behavior.
"""

import json
from pathlib import Path
from typing import Dict, Any

import pytest
from pdfserver.config import get_settings
from tests.integration.helpers import MockWebSocket


class TestInterfaceDefinitions:
    """Test suite for TypeScript interface definitions."""
    
    @pytest.fixture
    def viewer_ts_content(self):
        """Read viewer.ts and extract functions."""
        viewer_ts = Path(__file__).parent.parent.parent / "static" / "viewer.ts"
        if not viewer_ts.exists():
            pytest.skip("viewer.ts not found")
        return viewer_ts.read_text()
    
    @pytest.fixture
    def types_ts_content(self):
        """Read types.ts and extract interfaces."""
        types_ts = Path(__file__).parent.parent.parent / "static" / "types.ts"
        if not types_ts.exists():
            pytest.skip("types.ts not found")
        return types_ts.read_text()

    @pytest.fixture
    def coordinate_utils_ts_content(self):
        """Read coordinate-utils.ts and extract functions."""
        utils_ts = Path(__file__).parent.parent.parent / "static" / "coordinate-utils.ts"
        if not utils_ts.exists():
            pytest.skip("coordinate-utils.ts not found")
        return utils_ts.read_text()

    @pytest.fixture
    def pdfjs_types_content(self):
        """Read PDF.js type definitions."""
        types_file = Path(__file__).parent.parent.parent / "types" / "pdfjs.d.ts"
        if not types_file.exists():
            pytest.skip("pdfjs.d.ts not found")
        return types_file.read_text()
    
    def test_state_update_interface_structure(self, types_ts_content):
        """Test StateUpdate interface has correct structure."""
        content = types_ts_content
        
        # Check interface definition exists
        assert "interface StateUpdate" in content, "StateUpdate interface not found"
        
        # Check required fields
        assert "page: number" in content, "page field not found or wrong type"
        assert "y?: number" in content or "y: number | undefined" in content, "y field not optional"
        
        # Check optional fields
        assert "last_sync_time?: number" in content or "last_sync_time: number | undefined" in content, "last_sync_time field not found"
        assert "action?: string" in content or "action: string | undefined" in content, "action field not found"
    
    def test_pdf_config_interface_structure(self, types_ts_content):
        """Test PDFConfig interface has correct structure."""
        content = types_ts_content
        
        assert "interface PDFConfig" in content, "PDFConfig interface not found"
        assert "port: number" in content, "port field not found or wrong type"
        assert "filename: string" in content, "filename field not found or wrong type"
    
    def test_canvas_with_style_interface(self, types_ts_content):
        """Test CanvasWithStyle interface exists."""
        content = types_ts_content
        
        assert "interface CanvasWithStyle" in content, "CanvasWithStyle interface not found"
        assert "extends HTMLCanvasElement" in content or "HTMLCanvasElement" in content, "Should extend HTMLCanvasElement"
    
    def test_global_window_declaration(self, types_ts_content):
        """Test global Window interface extension."""
        content = types_ts_content
        
        assert "declare global" in content, "No global declarations found"
        assert "interface Window" in content, "Window interface not extended"
        assert "PDF_CONFIG: PDFConfig" in content, "PDF_CONFIG not declared on Window"
    
    def test_function_type_annotations(self, coordinate_utils_ts_content, viewer_ts_content):
        """Test key functions have proper type annotations."""
        utils_content = coordinate_utils_ts_content
        viewer_content = viewer_ts_content
        
        # Check function signatures
        assert "function getRenderScale(canvas: MockCanvas): number" in utils_content or \
               "function getRenderScale(canvas:" in utils_content, "getRenderScale not properly typed"
        
        assert "function pdfYToPixels(canvas: MockCanvas, y: number" in utils_content or \
               "function pdfYToPixels(canvas:" in utils_content, "pdfYToPixels not properly typed"
        
        assert "function applyStateUpdate(data: StateUpdate" in viewer_content, "applyStateUpdate not properly typed"
    
    def test_async_function_declarations(self, viewer_ts_content):
        """Test async functions are properly declared."""
        content = viewer_ts_content
        
        assert "async function reloadPDF(): Promise<void>" in content or \
               "async function reloadPDF()" in content, "reloadPDF not declared as async"
        
        assert "async function syncState(): Promise<void>" in content or \
               "async function syncState()" in content, "syncState not declared as async"


class TestPDFJSIntegration:
    """Test PDF.js TypeScript integration."""
    
    @pytest.fixture
    def pdf_renderer_ts_content(self):
        """Read pdf-renderer.ts and extract functions."""
        renderer_ts = Path(__file__).parent.parent.parent / "static" / "pdf-renderer.ts"
        if not renderer_ts.exists():
            pytest.skip("pdf-renderer.ts not found")
        return renderer_ts.read_text()

    @pytest.fixture
    def pdfjs_types_content(self):
        """Read PDF.js type definitions."""
        types_file = Path(__file__).parent.parent.parent / "types" / "pdfjs.d.ts"
        if not types_file.exists():
            pytest.skip("pdfjs.d.ts not found")
        return types_file.read_text()
    
    def test_pdf_page_proxy_type_exists(self, pdfjs_types_content):
        """Test PDFPageProxy type is defined."""
        assert "PDFPageProxy" in pdfjs_types_content, "PDFPageProxy type not found"
    
    def test_pdf_document_proxy_type_exists(self, pdfjs_types_content):
        """Test PDFDocumentProxy type is defined."""
        assert "PDFDocumentProxy" in pdfjs_types_content, "PDFDocumentProxy type not found"
    
    def test_pdfjs_import_in_viewer(self, pdf_renderer_ts_content):
        """Test PDF.js types are imported in pdf-renderer.ts."""
        assert "from '../types/pdfjs'" in pdf_renderer_ts_content, "PDF.js types not imported"


class TestTypeContracts:
    """Test runtime type contracts."""
    
    def test_api_response_types_match_interfaces(self, test_client, reset_state, mock_synctex):
        """Test that API responses have correct types."""
        # Update state using synctex params (line: 50, col: 5 -> page 5, y 505)
        response = test_client.post(
            "/webhook/update",
            json={"line": 50, "col": 5, "tex_file": "/path/to/test.tex", "pdf_file": str(get_settings().pdf_file)},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        # Check response types
        data = response.json()
        
        # page should be number (integer)
        assert isinstance(data["page"], int), f"page should be int, got {type(data['page'])}"
        assert data["page"] == 5
        
        # y should be number or null
        assert isinstance(data["y"], (float, type(None))), f"y should be float or null, got {type(data['y'])}"
        assert data["y"] == 505.0
        
        # x should be number or null (optional in TS)
        assert isinstance(data["x"], (float, int, type(None))), f"x should be number or null, got {type(data['x'])}"
        
        # status should be string
        assert isinstance(data["status"], str), f"status should be string, got {type(data['status'])}"
    
    def test_state_endpoint_returns_correct_types(self, test_client, reset_state):
        """Test /state returns correct types matching StateUpdate."""
        response = test_client.get("/state")
        assert response.status_code == 200
        
        data = response.json()
        
        # pdf_file: string | null (optional - null when no PDF loaded)
        assert isinstance(data["pdf_file"], (str, type(None))), f"pdf_file should be string or null, got {type(data['pdf_file'])}"
        
        # pdf_loaded: boolean (required - indicates if PDF is loaded)
        assert isinstance(data["pdf_loaded"], bool), f"pdf_loaded should be bool, got {type(data['pdf_loaded'])}"
        
        # page: number (required)
        assert isinstance(data["page"], int), "page should be int"
        
        # y: number | null
        assert isinstance(data["y"], (float, int, type(None))), "y should be number or null"
        
        # last_sync_time: number (required)
        assert isinstance(data["last_sync_time"], int), "last_sync_time should be int"
        assert data["last_sync_time"] > 0, "last_sync_time should be positive"


class TestTypeScriptNullHandling:
    """Test TypeScript null/undefined handling in integration."""
    
    @pytest.mark.asyncio
    async def test_nullish_coalescing_in_state(self, test_client, reset_state, reset_connections, mock_synctex):
        """Test that TypeScript nullish coalescing (??) works correctly at runtime."""
        from pdfserver.connection_manager import manager
        
        client = MockWebSocket()
        
        await manager.connect(client)
        
        # Test with synctex params that result in y = 0 (line: 0, col: 0)
        response = test_client.post(
            "/webhook/update",
            json={"line": 0, "col": 0, "tex_file": "/path/to/test.tex", "pdf_file": str(get_settings().pdf_file)},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # y should be 0.0, not null (line 0, col 0 -> page 1, y 0)
        assert "y" in client.sent_messages[0], "y key should be present"
        assert client.sent_messages[0]["y"] == 0.0, "y should be 0.0 (not null)"
        
        # Cleanup
        manager.disconnect(client)
    
    def test_optional_chaining_equivalent_behavior(self, test_client, reset_state, mock_synctex):
        """Test behavior equivalent to TypeScript optional chaining."""
        # Test with valid synctex params (line: 50 -> page 5, y 500)
        response = test_client.post(
            "/webhook/update",
            json={"line": 50, "col": 0, "tex_file": "/path/to/test.tex", "pdf_file": str(get_settings().pdf_file)},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # Response should handle fields gracefully
        data = response.json()
        assert "y" in data, "y should be present"
        assert data["y"] == 500.0, "y should be 500.0"


class TestViewerHTMLTypes:
    """Test viewer HTML contains correctly typed configuration."""
    
    def test_pdf_config_port_is_number(self, test_client, temp_pdf_file):
        """Test that port in PDF_CONFIG is a number, not string."""
        from pdfserver.config import get_settings
        
        response = test_client.get("/view")
        assert response.status_code == 200
        
        html = response.text
        settings = get_settings()
        
        # Port should appear as a number (no quotes in JSON context)
        # Look for pattern: port: 8080 (not port: "8080")
        import re
        
        # Find PDF_CONFIG in HTML
        config_match = re.search(r'window\.PDF_CONFIG\s*=\s*({[^}]+})', html)
        assert config_match, "PDF_CONFIG not found in HTML"
        
        config_str = config_match.group(1)
        
        # Port should not be quoted (indicating it's a number)
        port_pattern = rf'port:\s*{settings.port}(?!\d)'
        assert re.search(port_pattern, config_str), f"Port {settings.port} should be unquoted number"
