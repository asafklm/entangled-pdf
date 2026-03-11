"""Authentication endpoint for WebSocket token validation.

Handles token form submission and sets secure cookie for authenticated sessions.
"""

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from pdfserver.state import pdf_state

router = APIRouter()


@router.post("/auth")
async def authenticate(request: Request, token: str = Form(...)) -> Response:
    """Validate WebSocket authentication token and set session cookie.
    
    This endpoint receives the token from the browser form submission,
    validates it against the server's current token, and sets a secure
    HTTP-only cookie for subsequent authenticated requests.
    
    Args:
        request: The HTTP request
        token: The authentication token from the form
        
    Returns:
        RedirectResponse to /view with authentication cookie set
        
    Raises:
        HTTPException: 403 if token is invalid or inverse search not enabled
    """
    # Check if inverse search is enabled (requires HTTPS)
    if not pdf_state.inverse_search_enabled:
        raise HTTPException(
            status_code=403,
            detail="Inverse search not enabled. Server must use HTTPS."
        )
    
    # Validate token
    if token != pdf_state.websocket_token:
        raise HTTPException(status_code=403, detail="Invalid token")
    
    # Set secure cookie and redirect to viewer
    response = RedirectResponse(url="/view", status_code=303)
    response.set_cookie(
        key="pdf_token",
        value=token,
        httponly=True,  # Not accessible via JavaScript
        secure=True,    # Only sent over HTTPS
        samesite="strict",  # CSRF protection
        max_age=86400   # 24 hours
    )
    
    return response
