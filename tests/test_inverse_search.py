"""Tests for inverse search (backward sync) functionality.

Tests the token-based authentication system and inverse search (Shift+Click → Editor)
functionality. Inverse search is only available with HTTPS/WSS for security.
"""

import pytest
import asyncio
from pathlib import Path
from fastapi import FastAPI
from unittest.mock import patch, AsyncMock, MagicMock, mock_open

from pdfserver.routes import websocket as websocket_route, auth as auth_route, load_pdf as load_pdf_route
from pdfserver.routes import view as view_route
from pdfserver.state import pdf_state, generate_websocket_token
from pdfserver.connection_manager import ConnectionManager


@pytest.fixture(autouse=True)
def reset_state():
    """Reset pdf_state before each test."""
    pdf_state.websocket_token = generate_websocket_token()
    pdf_state.inverse_search_enabled = False
    pdf_state.inverse_search_command = None
    yield


class TestTokenGeneration:
    """Test suite for WebSocket token generation."""
    
    def test_generate_websocket_token_returns_string(self):
        """Test that token generation returns a non-empty string."""
        token = generate_websocket_token()
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_generate_websocket_token_unique(self):
        """Test that generated tokens are unique."""
        token1 = generate_websocket_token()
        token2 = generate_websocket_token()
        assert token1 != token2
    
    def test_generate_websocket_token_hex(self):
        """Test that tokens are hexadecimal (easily copiable)."""
        token = generate_websocket_token()
        # Hex tokens should only contain 0-9 and a-f
        assert all(c in '0123456789abcdef' for c in token)
        assert len(token) == 64  # 32 bytes = 64 hex chars


class TestWebSocketTokenValidation:
    """Test suite for WebSocket token validation."""
    
    @pytest.mark.asyncio
    async def test_websocket_without_token_rejected_when_inverse_enabled(self):
        """Test that WebSocket without token is rejected when inverse search enabled."""
        pdf_state.inverse_search_enabled = True
        pdf_state.websocket_token = "valid_token_123"
        
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()
        
        # Call without token
        await websocket_route.websocket_endpoint(mock_ws, token=None)
        
        # Should be rejected
        mock_ws.close.assert_called_once_with(code=4001, reason="Token required")
    
    @pytest.mark.asyncio
    async def test_websocket_with_invalid_token_rejected(self):
        """Test that WebSocket with invalid token is rejected."""
        pdf_state.inverse_search_enabled = True
        pdf_state.websocket_token = "valid_token_123"
        
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()
        
        # Call with wrong token
        await websocket_route.websocket_endpoint(mock_ws, token="wrong_token")
        
        # Should be rejected
        mock_ws.close.assert_called_once_with(code=4002, reason="Invalid token")
    
    @pytest.mark.asyncio
    async def test_websocket_with_valid_token_accepted(self):
        """Test that WebSocket with valid token is accepted."""
        pdf_state.inverse_search_enabled = True
        pdf_state.websocket_token = "valid_token_123"
        
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.receive_json = AsyncMock(side_effect=Exception("Stop loop"))
        
        # Call with valid token
        try:
            await websocket_route.websocket_endpoint(mock_ws, token="valid_token_123")
        except Exception:
            pass
        
        # Should be accepted
        mock_ws.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_without_token_allowed_when_inverse_disabled(self):
        """Test that WebSocket without token is allowed when inverse search disabled."""
        pdf_state.inverse_search_enabled = False
        
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.receive_json = AsyncMock(side_effect=Exception("Stop loop"))
        
        # Call without token, inverse search disabled
        try:
            await websocket_route.websocket_endpoint(mock_ws, token=None)
        except Exception:
            pass
        
        # Should be accepted (no token required when inverse search disabled)
        mock_ws.accept.assert_called_once()


class TestAuthEndpoint:
    """Test suite for authentication endpoint."""
    
    @pytest.mark.asyncio
    async def test_auth_with_valid_token_redirects(self):
        """Test that valid token redirects to viewer with cookie."""
        pdf_state.inverse_search_enabled = True
        pdf_state.websocket_token = "test_token_abc"
        
        from fastapi import Request
        mock_request = MagicMock(spec=Request)
        
        response = await auth_route.authenticate(
            mock_request, token="test_token_abc", c="0"
        )
        
        assert response.status_code == 303
        assert response.headers["location"] == "/view"
        # Check cookie is set
        assert "set-cookie" in response.headers
        assert "pdf_token=test_token_abc" in response.headers["set-cookie"]
    
    @pytest.mark.asyncio
    async def test_auth_with_invalid_token_redirects_with_error(self):
        """Test that invalid token redirects back to form with error counter."""
        pdf_state.inverse_search_enabled = True
        pdf_state.websocket_token = "test_token_abc"
        
        from fastapi import Request
        from fastapi.responses import RedirectResponse
        mock_request = MagicMock(spec=Request)
        
        response = await auth_route.authenticate(
            mock_request, token="wrong_token", c="0"
        )
        
        # Should redirect with error params
        assert isinstance(response, RedirectResponse)
        assert "/view" in str(response.headers.get('location', ''))
        assert "error=1" in str(response.headers.get('location', ''))
        assert "c=1" in str(response.headers.get('location', ''))
    
    @pytest.mark.asyncio
    async def test_auth_when_inverse_disabled_raises_403(self):
        """Test that auth raises 403 when inverse search not enabled."""
        pdf_state.inverse_search_enabled = False
        
        from fastapi import Request
        mock_request = MagicMock(spec=Request)
        
        with pytest.raises(Exception) as exc_info:
            await auth_route.authenticate(mock_request, token="any_token")
        
        assert "403" in str(exc_info.value) or "not enabled" in str(exc_info.value)


class TestViewPageAuthCheck:
    """Test suite for view page authentication check."""
    
    @pytest.mark.asyncio
    async def test_view_shows_token_form_when_not_authenticated(self):
        """Test that view shows token form when user not authenticated."""
        pdf_state.inverse_search_enabled = True
        pdf_state.websocket_token = "test_token"
        
        from fastapi import Request
        from fastapi.templating import Jinja2Templates
        
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {}  # No token cookie
        
        with patch.object(view_route, '_templates', None), \
             patch('pdfserver.routes.view.get_settings') as mock_settings, \
             patch('pdfserver.routes.view.Jinja2Templates') as mock_templates_class:
            
            mock_settings.return_value.pdf_file = None
            mock_settings.return_value.port = 8431
            mock_settings.return_value.static_dir = MagicMock()
            
            mock_templates = MagicMock()
            mock_templates_class.return_value = mock_templates
            mock_templates.TemplateResponse.return_value = MagicMock()
            
            await view_route.view_page(mock_request)
            
            # Should show token form
            mock_templates.TemplateResponse.assert_called_once()
            call_args = mock_templates.TemplateResponse.call_args
            assert call_args[0][1] == "token_form.html"
    
    @pytest.mark.asyncio
    async def test_view_shows_viewer_when_authenticated(self):
        """Test that view shows viewer when user authenticated."""
        pdf_state.inverse_search_enabled = True
        pdf_state.websocket_token = "test_token"
        
        from fastapi import Request
        from fastapi.templating import Jinja2Templates
        
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"pdf_token": "test_token"}  # Valid token
        
        with patch.object(view_route, '_templates', None), \
             patch('pdfserver.routes.view.get_settings') as mock_settings, \
             patch('pdfserver.routes.view.Jinja2Templates') as mock_templates_class:
            
            mock_settings.return_value.pdf_file = None
            mock_settings.return_value.port = 8431
            mock_settings.return_value.static_dir = MagicMock()
            
            mock_templates = MagicMock()
            mock_templates_class.return_value = mock_templates
            mock_templates.TemplateResponse.return_value = MagicMock()
            
            await view_route.view_page(mock_request)
            
            # Should show viewer
            mock_templates.TemplateResponse.assert_called_once()
            call_args = mock_templates.TemplateResponse.call_args
            assert call_args[0][1] == "viewer.html"


class TestLoadPdfWithInverseSearch:
    """Test suite for load PDF endpoint with inverse search configuration."""
    
    @pytest.mark.asyncio
    async def test_load_pdf_with_inverse_search_enables_feature(self):
        """Test that loading PDF with inverse search command enables feature."""
        from pdfserver.config import Settings
        
        with patch('pdfserver.routes.load_pdf.get_settings') as mock_settings, \
             patch('pdfserver.routes.load_pdf.manager') as mock_manager:
            
            mock_settings.return_value = MagicMock(spec=Settings)
            mock_settings.return_value.api_key = "test_secret"
            mock_settings.return_value.use_https = True
            mock_settings.return_value.pdf_file = None
            
            mock_manager.broadcast = AsyncMock()
            
            pdf_path = "/tmp/test.pdf"
            inverse_cmd = "nvr --remote-silent +%{line} %{file}"
            
            data = {
                "pdf_path": pdf_path,
                "inverse_search_command": inverse_cmd
            }
            
            with patch.object(Path, 'exists', return_value=True), \
                 patch.object(Path, 'resolve', return_value=Path(pdf_path)), \
                 patch.object(Path, 'stat') as mock_stat, \
                 patch('pdfserver.routes.load_pdf.validate_pdf_file', return_value=(True, "")):
                
                mock_stat_result = MagicMock()
                mock_stat_result.st_mtime = 12345
                mock_stat.return_value = mock_stat_result
                
                response = await load_pdf_route.load_pdf(data, x_api_key="test_secret")
            
            assert response.status_code == 200
            response_data = response.body.decode()
            assert "websocket_token" in response_data
            assert pdf_state.inverse_search_enabled is True
            assert pdf_state.inverse_search_command == inverse_cmd
    
    @pytest.mark.asyncio
    async def test_load_pdf_http_does_not_enable_inverse_search(self):
        """Test that loading PDF via HTTP does not enable inverse search."""
        from pdfserver.config import Settings
        
        with patch('pdfserver.routes.load_pdf.get_settings') as mock_settings, \
             patch('pdfserver.routes.load_pdf.manager') as mock_manager:
            
            mock_settings.return_value = MagicMock(spec=Settings)
            mock_settings.return_value.api_key = "test_secret"
            mock_settings.return_value.use_https = False  # HTTP mode
            mock_settings.return_value.pdf_file = None
            
            mock_manager.broadcast = AsyncMock()
            
            pdf_path = "/tmp/test.pdf"
            inverse_cmd = "nvr --remote-silent +%{line} %{file}"
            
            data = {
                "pdf_path": pdf_path,
                "inverse_search_command": inverse_cmd
            }
            
            with patch.object(Path, 'exists', return_value=True), \
                 patch.object(Path, 'resolve', return_value=Path(pdf_path)), \
                 patch.object(Path, 'stat') as mock_stat, \
                 patch('pdfserver.routes.load_pdf.validate_pdf_file', return_value=(True, "")):
                
                mock_stat_result = MagicMock()
                mock_stat_result.st_mtime = 12345
                mock_stat.return_value = mock_stat_result
                
                response = await load_pdf_route.load_pdf(data, x_api_key="test_secret")
            
            assert response.status_code == 200
            response_data = response.body.decode()
            # Should not include websocket_token in HTTP mode
            assert "websocket_token" not in response_data
            assert pdf_state.inverse_search_enabled is False


class TestInverseSearchExecution:
    """Test suite for inverse search execution."""
    
    @pytest.mark.asyncio
    async def test_run_synctex_edit_success(self):
        """Test successful synctex edit command execution."""
        from unittest.mock import AsyncMock as MockAsync
        
        mock_process = MockAsync()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(
            b"Input:/path/to/file.tex\nLine:42\nColumn:5\n",
            b""
        ))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await websocket_route.run_synctex_edit(5, 100.0, 200.0, "/tmp/test.pdf")
        
        assert result is not None
        assert result.get("Input") == "/path/to/file.tex"
        assert result.get("Line") == "42"
    
    @pytest.mark.asyncio
    async def test_run_synctex_edit_failure(self):
        """Test synctex edit command failure handling."""
        from unittest.mock import AsyncMock as MockAsync
        
        mock_process = MockAsync()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error"))
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await websocket_route.run_synctex_edit(5, 100.0, 200.0, "/tmp/test.pdf")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_execute_inverse_search_disabled(self):
        """Test that execute_inverse_search returns False when disabled."""
        pdf_state.inverse_search_enabled = False
        pdf_state.pdf_file = Path("/tmp/test.pdf")
        
        result = await websocket_route.execute_inverse_search(5, 100.0, 200.0)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_execute_inverse_search_no_command(self):
        """Test that execute_inverse_search returns False when no command set."""
        pdf_state.inverse_search_enabled = True
        pdf_state.inverse_search_command = None
        pdf_state.pdf_file = Path("/tmp/test.pdf")
        
        result = await websocket_route.execute_inverse_search(5, 100.0, 200.0)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_execute_inverse_search_no_pdf(self):
        """Test that execute_inverse_search returns False when no PDF loaded."""
        pdf_state.inverse_search_enabled = True
        pdf_state.inverse_search_command = "nvr +%{line} %{file}"
        pdf_state.pdf_file = None
        
        result = await websocket_route.execute_inverse_search(5, 100.0, 200.0)
        
        assert result is False


class TestInverseSearchMessageHandling:
    """Test suite for inverse search WebSocket message handling."""
    
    @pytest.mark.asyncio
    async def test_inverse_search_message_processed(self):
        """Test that inverse search messages are processed correctly."""
        pdf_state.inverse_search_enabled = True
        pdf_state.websocket_token = "valid_token"
        pdf_state.inverse_search_command = "nvr +%{line} %{file}"
        pdf_state.pdf_file = Path("/tmp/test.pdf")
        
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        
        message_count = [0]
        async def receive_side_effect():
            message_count[0] += 1
            if message_count[0] == 1:
                return {
                    "action": "inverse_search",
                    "page": 5,
                    "x": 100.0,
                    "y": 200.0
                }
            else:
                from fastapi import WebSocketDisconnect
                raise WebSocketDisconnect()
        
        mock_ws.receive_json = AsyncMock(side_effect=receive_side_effect)
        
        with patch.object(websocket_route, 'execute_inverse_search', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = True
            
            await websocket_route.websocket_endpoint(mock_ws, token="valid_token")
            
            # Verify execute_inverse_search was called with correct params
            mock_execute.assert_called_once_with(5, 100.0, 200.0)
    
    @pytest.mark.asyncio
    async def test_inverse_search_message_ignored_when_disabled(self):
        """Test that inverse search messages are ignored when feature disabled."""
        pdf_state.inverse_search_enabled = False
        pdf_state.websocket_token = "valid_token"
        
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        
        message_count = [0]
        async def receive_side_effect():
            message_count[0] += 1
            if message_count[0] == 1:
                return {
                    "action": "inverse_search",
                    "page": 5,
                    "x": 100.0,
                    "y": 200.0
                }
            else:
                from fastapi import WebSocketDisconnect
                raise WebSocketDisconnect()
        
        mock_ws.receive_json = AsyncMock(side_effect=receive_side_effect)
        
        with patch.object(websocket_route, 'execute_inverse_search', new_callable=AsyncMock) as mock_execute:
            await websocket_route.websocket_endpoint(mock_ws, token="valid_token")
            
            # Verify execute_inverse_search was NOT called
            mock_execute.assert_not_called()
