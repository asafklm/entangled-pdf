"""Tests for entangledpdf.routes.auth.authenticate."""

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi import HTTPException

from entangledpdf.routes import auth as auth_route
from entangledpdf.state import pdf_state


@pytest.fixture
def app():
    """Create FastAPI app with auth router."""
    app = FastAPI()
    app.include_router(auth_route.router)
    return app


@pytest.mark.asyncio
async def test_auth_success_sets_cookie(app):
    old_inverse = pdf_state.inverse_search_enabled
    old_token = pdf_state.websocket_token
    pdf_state.inverse_search_enabled = True
    pdf_state.websocket_token = "TEST-TOKEN-ABC"

    client = TestClient(app)
    resp = client.post("/auth", data={"token": "TEST-TOKEN-ABC"}, follow_redirects=False)
    assert resp.status_code == 303
    set_cookie = resp.headers.get("set-cookie", "")
    assert "pdf_token=TEST-TOKEN-ABC" in set_cookie

    pdf_state.inverse_search_enabled = old_inverse
    pdf_state.websocket_token = old_token


@pytest.mark.asyncio
async def test_auth_invalid_token_redirects(app):
    pdf_state.inverse_search_enabled = True
    pdf_state.websocket_token = "VALID"
    
    client = TestClient(app)
    resp = client.post("/auth", data={"token": "BAD"}, follow_redirects=False)
    assert resp.status_code == 303
    assert "error=1" in resp.headers["location"]


@pytest.mark.asyncio
async def test_auth_inverse_not_enabled_raises(app):
    pdf_state.inverse_search_enabled = False
    
    client = TestClient(app)
    resp = client.post("/auth", data={"token": "ANY"}, follow_redirects=False)
    assert resp.status_code == 403
