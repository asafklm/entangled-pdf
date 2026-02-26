"""Integration tests for TypeScript build process.

Tests that TypeScript compiles correctly and generates valid output.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from src.config import get_settings
from tests.integration.helpers import MockWebSocket


class TestTypeScriptCompilation:
    """Test suite for TypeScript build integration."""
    
    @pytest.fixture(scope="class")
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent
    
    def test_typescript_compiles_without_errors(self, project_root):
        """Test that TypeScript compiler runs without errors."""
        # Check if TypeScript compiler is available
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        # TypeScript should compile without errors
        assert result.returncode == 0, f"TypeScript compilation failed:\n{result.stdout}\n{result.stderr}"
    
    def test_viewer_ts_exists(self, project_root):
        """Test that viewer.ts source file exists."""
        viewer_ts = project_root / "static" / "viewer.ts"
        assert viewer_ts.exists(), "viewer.ts not found"
        assert viewer_ts.stat().st_size > 0, "viewer.ts is empty"
    
    def test_compiled_js_exists(self, project_root):
        """Test that compiled viewer.js exists."""
        viewer_js = project_root / "static" / "viewer.js"
        
        # If viewer.ts exists, viewer.js should also exist (or be compilable)
        viewer_ts = project_root / "static" / "viewer.ts"
        
        if viewer_ts.exists():
            # Ensure it's compiled
            if not viewer_js.exists():
                result = subprocess.run(
                    ["npm", "run", "build"],
                    cwd=project_root,
                    capture_output=True,
                    text=True
                )
                assert result.returncode == 0, "Failed to compile TypeScript"
            
            assert viewer_js.exists(), "viewer.js not found after compilation"
            assert viewer_js.stat().st_size > 0, "viewer.js is empty"
    
    def test_compiled_js_is_valid_javascript(self, project_root):
        """Test that compiled output is valid JavaScript."""
        viewer_js = project_root / "static" / "viewer.js"
        
        if not viewer_js.exists():
            pytest.skip("viewer.js not found")
        
        content = viewer_js.read_text()
        
        # Basic JavaScript validation
        assert content.strip(), "viewer.js is empty"
        assert "function" in content or "=>" in content, "No functions found"
        assert "const" in content or "let" in content or "var" in content, "No variables found"
        
        # Should not have TypeScript-specific syntax in output
        assert ": number" not in content, "TypeScript type annotations found in output"
        assert ": string" not in content, "TypeScript type annotations found in output"
        assert "interface " not in content, "TypeScript interfaces found in output"
    
    def test_build_script_exists(self, project_root):
        """Test that npm build script is configured."""
        package_json = project_root / "package.json"
        
        if not package_json.exists():
            pytest.skip("package.json not found")
        
        import json
        with open(package_json) as f:
            pkg = json.load(f)
        
        assert "scripts" in pkg, "No scripts section in package.json"
        assert "build" in pkg["scripts"], "No build script in package.json"
    
    def test_compiled_output_has_required_functions(self, project_root):
        """Test that compiled JS has required functions."""
        viewer_js = project_root / "static" / "viewer.js"
        
        if not viewer_js.exists():
            pytest.skip("viewer.js not found")
        
        content = viewer_js.read_text()
        
        # Check for key functions
        required_functions = [
            "loadPDF",
            "connectWebSocket",
            "scrollToPage",
            "applyStateUpdate",
            "syncState"
        ]
        
        for func in required_functions:
            assert func in content, f"Required function '{func}' not found in compiled JS"
    
    def test_type_definitions_exist(self, project_root):
        """Test that TypeScript type definitions are present."""
        # Check for PDF.js type definitions
        types_dir = project_root / "types"
        
        if types_dir.exists():
            pdfjs_dts = types_dir / "pdfjs.d.ts"
            if pdfjs_dts.exists():
                content = pdfjs_dts.read_text()
                assert "PDFPageProxy" in content or "PDFDocumentProxy" in content, "PDF.js types not found"


class TestTypeScriptInterfaceContracts:
    """Test that TypeScript interfaces match runtime behavior."""
    
    @pytest.fixture
    def viewer_ts_content(self):
        """Read viewer.ts content."""
        viewer_ts = Path(__file__).parent.parent.parent / "static" / "viewer.ts"
        if not viewer_ts.exists():
            pytest.skip("viewer.ts not found")
        return viewer_ts.read_text()
    
    def test_state_update_interface_matches_api(self, viewer_ts_content, test_client, reset_state):
        """Test that StateUpdate interface matches /state API response."""
        # Get actual API response
        response = test_client.post(
            "/webhook/update",
            json={"line": 10, "col": 5, "tex_file": "/path/to/test.tex", "pdf_file": str(get_settings().pdf_file)},
            headers={"X-API-Key": get_settings().secret}
        )
        assert response.status_code == 200
        
        response = test_client.get("/state")
        api_data = response.json()
        
        # Verify API fields match StateUpdate interface
        assert "pdf_file" in api_data, "API missing 'pdf_file' field"
        assert "page" in api_data, "API missing 'page' field"
        assert "y" in api_data, "API missing 'y' field"
        assert "last_update_time" in api_data, "API missing 'last_update_time' field"
        
        # Type checks
        assert isinstance(api_data["pdf_file"], str), "pdf_file should be string"
        assert isinstance(api_data["page"], int), "page should be number (int)"
        assert isinstance(api_data["y"], (float, type(None))), "y should be number or null"
        assert isinstance(api_data["last_update_time"], int), "last_update_time should be number"
    
    def test_pdf_config_interface_matches_backend(self, viewer_ts_content, test_client, test_settings):
        """Test that PDFConfig interface matches window.PDF_CONFIG from backend."""
        # Get viewer HTML which contains PDF_CONFIG
        response = test_client.get("/view")
        assert response.status_code == 200
        
        html = response.text
        
        # Verify PDF_CONFIG is present with correct fields
        assert "PDF_CONFIG" in html, "PDF_CONFIG not found in HTML"
        assert str(test_settings.port) in html, "Port not in PDF_CONFIG"
        assert test_settings.pdf_file.name in html, "Filename not in PDF_CONFIG"
    
    @pytest.mark.asyncio
    async def test_websocket_message_format_matches_interface(self, test_client, reset_state, reset_connections, mock_synctex):
        """Test that WebSocket message format matches StateUpdate interface."""
        from src.connection_manager import manager
        
        client = MockWebSocket()
        
        await manager.connect(client)
        
        # Send webhook with synctex params (line: 30, col: 5 -> page 3, y 305, x 25)
        response = test_client.post(
            "/webhook/update",
            json={"line": 30, "col": 5, "tex_file": "/path/to/test.tex", "pdf_file": str(get_settings().pdf_file)},
            headers={"X-API-Key": get_settings().secret}
        )
        
        assert response.status_code == 200
        
        # Verify WebSocket message format
        assert len(client.sent_messages) == 1
        msg = client.sent_messages[0]
        
        # Fields that StateUpdate expects
        assert "page" in msg, "WebSocket message missing 'page'"
        assert "y" in msg, "WebSocket message missing 'y'"
        assert "action" in msg, "WebSocket message missing 'action'"
        assert "timestamp" in msg, "WebSocket message missing 'timestamp'"
        
        # Types
        assert isinstance(msg["page"], int)
        assert isinstance(msg["y"], (int, float, type(None)))
        assert isinstance(msg["action"], str)
        assert isinstance(msg["timestamp"], int)
        
        # Values (line 30, col 5 -> page 3, y 305, x 25)
        assert msg["page"] == 3
        assert msg["y"] == 305.0
        assert msg["x"] == 25.0
        
        # Cleanup
        manager.disconnect(client)


class TestBuildFailureScenarios:
    """Test build failure scenarios."""
    
    @pytest.fixture(scope="class")
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent
    
    def test_build_fails_on_syntax_error(self, project_root, tmp_path):
        """Test that build fails when there's a syntax error."""
        # Create a file with intentional syntax error
        test_ts = tmp_path / "test_error.ts"
        test_ts.write_text("const x: string = 123; // Type error: number assigned to string")
        
        # Try to compile
        result = subprocess.run(
            ["npx", "tsc", "--noEmit", str(test_ts)],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        # Should fail due to type error
        assert result.returncode != 0 or "error" in result.stderr.lower()
