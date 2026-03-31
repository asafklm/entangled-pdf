"""Static Build Validation Tests for PdfServer.

Tests that verify the build artifacts meet structural requirements
and don't contain anti-patterns that could cause runtime issues.

These tests catch issues like:
- Race conditions from CDN-based dependencies
- Missing ES module declarations
- Global variable anti-patterns
- Unserved static assets
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestCDNUsageValidation:
    """Tests to prevent CDN-based dependency issues."""
    
    @pytest.fixture(scope="class")
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent
    
    def test_no_cdn_urls_in_html_templates(self, project_root):
        """Verify no CDN URLs in HTML templates - prevents external dependency failures."""
        # Find all HTML templates
        html_files = list(project_root.rglob("*.html"))
        
        cdn_patterns = [
            "cdnjs.cloudflare.com",
            "cdn.jsdelivr.net",
            "unpkg.com",
            "cdnjs.com",
        ]
        
        violations = []
        
        for html_file in html_files:
            content = html_file.read_text()
            for cdn in cdn_patterns:
                if cdn in content:
                    # Find line number
                    for i, line in enumerate(content.split("\n"), 1):
                        if cdn in line:
                            violations.append(f"{html_file}:{i}: {cdn}")
        
        if violations:
            pytest.fail(
                f"Found CDN URLs in templates (can cause race conditions if blocked):\n" + 
                "\n".join(violations)
            )
    
    def test_no_hardcoded_external_dependencies_in_js(self, project_root):
        """Verify no hardcoded external URLs in JavaScript files."""
        js_files = list((project_root / "static").glob("*.js"))
        
        external_patterns = [
            "https://",
            "http://",
        ]
        
        allowed_domains = [
            # Local paths are always OK
            "/static/",
            "/pdfjs/",
            "/get-pdf",
            "/state",
            "/webhook/",
            "/ws",
        ]
        
        violations = []
        
        for js_file in js_files:
            content = js_file.read_text()
            lines = content.split("\n")
            
            for i, line in enumerate(lines, 1):
                for pattern in external_patterns:
                    if pattern in line and not any(allowed in line for allowed in allowed_domains):
                        # Skip comments
                        stripped = line.strip()
                        if not stripped.startswith("//") and not stripped.startswith("*"):
                            violations.append(f"{js_file}:{i}: {line.strip()[:80]}")
        
        # Allow comments about external resources
        violations = [v for v in violations if "cdnjs" in v or "cdn." in v]
        
        if violations:
            pytest.fail(
                f"Found external URLs in JavaScript (can fail if network unavailable):\n" +
                "\n".join(violations)
            )


class TestESModuleValidation:
    """Tests to verify correct ES module usage."""
    
    @pytest.fixture(scope="class")
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent
    
    def test_viewer_js_uses_es_module_import(self, project_root):
        """Verify viewer.js uses ES module import for pdfjsLib.
        
        This test catches the race condition where pdfjsLib was accessed
        as a global before the CDN script loaded.
        """
        viewer_js = project_root / "static" / "viewer.js"
        
        if not viewer_js.exists():
            pytest.skip("viewer.js not found")
        
        content = viewer_js.read_text()
        
        # Must use ES module import
        assert "import * as pdfjsLib from" in content, (
            "viewer.js must use ES module import for pdfjsLib. "
            "This prevents race conditions where the library isn't loaded yet."
        )
        
        # Should NOT access pdfjsLib as global variable
        assert "window.pdfjsLib" not in content, (
            "viewer.js should not access pdfjsLib via window global. "
            "Use ES module import instead to ensure proper loading order."
        )
    
    def test_pdf_renderer_ts_uses_module_import(self, project_root):
        """Verify pdf-renderer.ts source uses module import pattern."""
        renderer_ts = project_root / "static" / "pdf-renderer.ts"
        
        if not renderer_ts.exists():
            pytest.skip("pdf-renderer.ts not found")
        
        content = renderer_ts.read_text()
        
        # Must import pdfjsLib as module
        assert "import * as pdfjsLib from" in content, (
            "pdf-renderer.ts must use ES module import. "
            "Pattern: import * as pdfjsLib from '/pdfjs/pdf.mjs'"
        )
        
        # Should NOT declare pdfjsLib as a global
        # Check inside declare global blocks specifically
        if "declare global" in content:
            lines = content.split("\n")
            in_global_decl = False
            brace_count = 0
            
            for i, line in enumerate(lines, 1):
                if "declare global" in line:
                    in_global_decl = True
                    brace_count = line.count("{") - line.count("}")
                    continue
                
                if in_global_decl:
                    brace_count += line.count("{") - line.count("}")
                    
                    # Check if pdfjsLib is declared inside the global block
                    if "pdfjsLib" in line and "interface" in line:
                        pytest.fail(
                            f"pdf-renderer.ts line {i}: Should not declare pdfjsLib as global. "
                            "Import it as ES module instead.\n"
                            f"Found: {line.strip()}"
                        )
                    
                    if brace_count <= 0:
                        in_global_decl = False


class TestStaticFileServing:
    """Tests to verify all static assets are properly served."""
    
    def test_pdfjs_files_are_served(self, real_test_client: TestClient):
        """Verify PDF.js files return 200 OK."""
        # Main PDF.js module
        response = real_test_client.get("/pdfjs/pdf.mjs")
        assert response.status_code == 200, (
            f"/pdfjs/pdf.mjs returned {response.status_code}. "
            "PDF.js main module must be accessible."
        )
        assert "application/javascript" in response.headers.get("content-type", "") or \
               response.headers.get("content-type", "").startswith("text/"), (
            "pdf.mjs should have JavaScript content type"
        )
        
        # PDF.js worker
        response = real_test_client.get("/pdfjs/pdf.worker.mjs")
        assert response.status_code == 200, (
            f"/pdfjs/pdf.worker.mjs returned {response.status_code}. "
            "PDF.js worker must be accessible."
        )
    
    def test_viewer_js_is_served_as_module(self, real_test_client: TestClient):
        """Verify viewer.js is accessible."""
        response = real_test_client.get("/static/viewer.js")
        assert response.status_code == 200, (
            f"/static/viewer.js returned {response.status_code}. "
            "Viewer JavaScript must be accessible."
        )
        
        content = response.text
        assert len(content) > 1000, "viewer.js seems too small, may be incomplete"
    
    def test_worker_source_is_local(self, real_test_client: TestClient):
        """Verify PDF.js worker is loaded from local path, not CDN."""
        response = real_test_client.get("/static/viewer.js")
        assert response.status_code == 200
        
        content = response.text
        
        # Worker should point to local path
        assert "pdf.worker.mjs" in content, (
            "viewer.js must reference local pdf.worker.mjs. "
            "Look for: pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdfjs/pdf.worker.mjs'"
        )
        
        # Should NOT reference CDN for worker
        assert "cdnjs.cloudflare.com" not in content, (
            "viewer.js should not reference CDN for PDF.js worker. "
            "Use local path: /pdfjs/pdf.worker.mjs"
        )


class TestBuildArtifactConsistency:
    """Tests to verify build artifacts are consistent with source."""
    
    @pytest.fixture(scope="class")
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent
    
    def test_compiled_js_matches_source_structure(self, project_root):
        """Verify compiled JS has same import structure as source.
        
        Catches cases where compilation changes module semantics.
        """
        viewer_ts = project_root / "static" / "viewer.ts"
        viewer_js = project_root / "static" / "viewer.js"
        
        if not viewer_ts.exists() or not viewer_js.exists():
            pytest.skip("Source or compiled file not found")
        
        ts_content = viewer_ts.read_text()
        js_content = viewer_js.read_text()
        
        # If source has ES module import, compiled should too
        if "import * as pdfjsLib from" in ts_content:
            assert "import * as pdfjsLib from" in js_content, (
                "ES module import was lost during TypeScript compilation. "
                "Check tsconfig.json module settings."
            )
    
    def test_no_commonjs_require_in_output(self, project_root):
        """Verify output doesn't use CommonJS require (should use ES modules)."""
        viewer_js = project_root / "static" / "viewer.js"
        
        if not viewer_js.exists():
            pytest.skip("viewer.js not found")
        
        content = viewer_js.read_text()
        
        assert "require(" not in content, (
            "viewer.js should not use CommonJS require(). "
            "Must use ES module import syntax for browser compatibility."
        )
        assert "module.exports" not in content, (
            "viewer.js should not use CommonJS module.exports. "
            "Must use ES module export syntax."
        )
