"""Integration tests for TypeScript interface contracts.

Tests that TypeScript type definitions match actual runtime behavior.
"""

import json
from pathlib import Path
from typing import Dict, Any

import pytest
from src.config import get_settings
from tests.integration.helpers import MockWebSocket


class TestInterfaceDefinitions:
    """Test suite for TypeScript interface definitions."""
    
    @pytest.fixture
    def viewer_ts_content(self):
        """Read viewer.ts and extract interfaces."""
        viewer_ts = Path(__file__).parent.parent.parent / "static" / "viewer.ts"
        if not viewer_ts.exists():
            pytest.skip("viewer.ts not found")
        return viewer_ts.read_text()
    
    @pytest.fixture
    def pdfjs_types_content(self):
        """Read PDF.js type definitions."""
        types_file = Path(__file__).parent.parent.parent / "types" / "pdfjs.d.ts"
        if not types_file.exists():
            pytest.skip("pdfjs.d.ts not found")
        return types_file.read_text()
    
    def test_state_update_interface_structure(self, viewer_ts_content):
        """Test StateUpdate interface has correct structure."""
        content = viewer_ts_content
        
        # Check interface definition exists
        assert "interface StateUpdate" in content, "StateUpdate interface not found"
        
        # Check required fields
        assert "page: number" in content, "page field not found or wrong type"
        assert "y?: number" in content or "y: number | undefined" in content, "y field not optional"
        
        # Check optional fields
        assert "timestamp?: number" in content or "timestamp: number | undefined" in content, "timestamp field not found"
        assert "last_update_time?: number" in content or "last_update_time: number | undefined" in content, "last_update_time field not found"
        assert "action?: string" in content or "action: string | undefined" in content, "action field not found"
    
    def test_pdf_config_interface_structure(self, viewer_ts_content):
        """Test PDFConfig interface has correct structure."""
        content = viewer_ts_content
        
        assert "interface PDFConfig" in content, "PDFConfig interface not found"
        assert "port: number" in content, "port field not found or wrong type"
        assert "filename: string" in content, "filename field not found or wrong type"
    
    def test_canvas_with_style_interface(self, viewer_ts_content):
        """Test CanvasWithStyle interface exists."""
        content = viewer_ts_content
        
        assert "interface CanvasWithStyle" in content, "CanvasWithStyle interface not found"
        assert "extends HTMLCanvasElement" in content or "HTMLCanvasElement" in content, "Should extend HTMLCanvasElement"
    
    def test_global_window_declaration(self, viewer_ts_content):
        """Test global Window interface extension."""
        content = viewer_ts_content
        
        assert "declare global" in content, "No global declarations found"
        assert "interface Window" in content, "Window interface not extended"
        assert "PDF_CONFIG: PDFConfig" in content, "PDF_CONFIG not declared on Window"
    
    def test_function_type_annotations(self, viewer_ts_content):
        """Test key functions have proper type annotations."""
        content = viewer_ts_content
        
        # Check function signatures
        assert "function getRenderScale(canvas: CanvasWithStyle): number" in content or \
               "function getRenderScale(canvas:" in content, "getRenderScale not properly typed"
        
        assert "function pdfYToPixels(canvas: CanvasWithStyle, y: number): number" in content or \
               "function pdfYToPixels(canvas:" in content, "pdfYToPixels not properly typed"
        
        assert "function applyStateUpdate(data: StateUpdate" in content, "applyStateUpdate not properly typed"
    
    def test_async_function_declarations(self, viewer_ts_content):
        """Test async functions are properly declared."""
        content = viewer_ts_content
        
        assert "async function loadPDF(): Promise<void>" in content or \
               "async function loadPDF()" in content, "loadPDF not declared as async"
        
        assert "async function syncState(): Promise<void>" in content or \
               "async function syncState()" in content, "syncState not declared as async"


class TestPDFJSIntegration:
    """Test PDF.js TypeScript integration."""
    
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
    
    def test_pdfjs_import_in_viewer(self, viewer_ts_content):
        """Test PDF.js types are imported in viewer.ts."""
        assert "from '../types/pdfjs'" in viewer_ts_content, "PDF.js types not imported"


class TestTypeContracts:
    """Test runtime type contracts."""
    
    def test_api_response_types_match_interfaces(self, test_client, reset_state):
        """Test that API responses have correct types."""
        # Update state
        response = test_client.post(
            "/webhook/update",
            json={"page": 5, "y": 150.5},
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
        assert data["y"] == 150.5
        
        # x should be number or null (optional in TS)
        assert isinstance(data["x"], (float, int, type(None))), f"x should be number or null, got {type(data['x'])}"
        
        # status should be string
        assert isinstance(data["status"], str), f"status should be string, got {type(data['status'])}"
    
    def test_state_endpoint_returns_correct_types(self, test_client, reset_state):
        """Test /state returns correct types matching StateUpdate."""
        response = test_client.get("/state")
        assert response.status_code == 200
        
        data = response.json()
        
        # pdf_file: string (required)
        assert isinstance(data["pdf_file"], str), "pdf_file should be string"
        
        # page: number (required)
        assert isinstance(data["page"], int), "page should be int"
        
        # y: number | null
        assert isinstance(data["y"], (float, int, type(None))), "y should be number or null"
        
        # last_update_time: number (required)
        assert isinstance(data["last_update_time"], int), "last_update_time should be int"
        assert data["last_update_time"] > 0, "last_update_time should be positive"


class TestTypeScriptNullHandling:
    """Test TypeScript null/undefined handling in integration."""
    
    @pytest.mark.asyncio
    async def test_nullish_coalescing_in_state(self, test_client, reset_state, reset_connections):
        """Test that TypeScript nullish coalescing (??) works correctly at runtime."""
        from src.connection_manager import manager
        
        client = MockWebSocket()
        
        await manager.connect(client)
        
        # Test with y = null (should be preserved as null, not undefined)
        response = test_client.post(
            "/webhook/update",
            json={"page": 3, "y": None},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # y should be null (not undefined, which would be missing key)
        assert "y" in client.sent_messages[0], "y key should be present"
        assert client.sent_messages[0]["y"] is None, "y should be null"
        
        # Cleanup
        manager.disconnect(client)
    
    def test_optional_chaining_equivalent_behavior(self, test_client, reset_state):
        """Test behavior equivalent to TypeScript optional chaining."""
        # Test with missing optional fields
        response = test_client.post(
            "/webhook/update",
            json={"page": 5},  # No y, x, timestamp
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # Response should handle missing fields gracefully
        data = response.json()
        assert "y" in data, "y should be present (as null)"
        assert data["y"] is None, "y should be null when not provided"


class TestViewerHTMLTypes:
    """Test viewer HTML contains correctly typed configuration."""
    
    def test_pdf_config_port_is_number(self, test_client, temp_pdf_file):
        """Test that port in PDF_CONFIG is a number, not string."""
        from src.config import get_settings
        
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
