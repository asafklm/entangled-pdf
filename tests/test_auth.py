"""Tests for src.routes.auth.authenticate."""

import asyncio

import pytest
from fastapi import HTTPException

from pdfserver.routes.auth import authenticate
from pdfserver.state import pdf_state


@pytest.mark.asyncio
async def test_auth_success_sets_cookie():
    old_inverse = pdf_state.inverse_search_enabled
    old_token = pdf_state.websocket_token
    pdf_state.inverse_search_enabled = True
    pdf_state.websocket_token = "TEST-TOKEN-ABC"

    resp = await authenticate(None, token="TEST-TOKEN-ABC")  # type: ignore[arg-type]
    assert resp.status_code == 303
    set_cookie = resp.headers.get("set-cookie", "")
    assert "pdf_token=TEST-TOKEN-ABC" in set_cookie

    pdf_state.inverse_search_enabled = old_inverse
    pdf_state.websocket_token = old_token


@pytest.mark.asyncio
async def test_auth_invalid_token_raises():
    pdf_state.inverse_search_enabled = True
    pdf_state.websocket_token = "VALID"
    with pytest.raises(HTTPException):
        await authenticate(None, token="BAD")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_auth_inverse_not_enabled_raises():
    pdf_state.inverse_search_enabled = False
    with pytest.raises(HTTPException):
        await authenticate(None, token="ANY")  # type: ignore[arg-type]
