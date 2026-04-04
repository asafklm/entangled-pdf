from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient

from entangledpdf.routes import auth
from entangledpdf.state import pdf_state


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(auth.router)
    return app


def test_auth_success_sets_secure_cookie_and_redirect(monkeypatch) -> None:
    # Setup state for successful auth
    pdf_state.inverse_search_enabled = True
    pdf_state.websocket_token = "token-123"

    app = _make_app()
    client = TestClient(app)

    resp = client.post("/auth", data={"token": "token-123"}, follow_redirects=False)

    assert resp.status_code == HTTPStatus.SEE_OTHER
    assert resp.headers["location"] == "/view"
    # Cookie should be set for pdf_token
    cookies = resp.cookies
    assert cookies.get("pdf_token") == "token-123"


def test_auth_forbidden_when_inverse_search_disabled() -> None:
    pdf_state.inverse_search_enabled = False
    pdf_state.websocket_token = "token-xyz"

    app = _make_app()
    client = TestClient(app)

    resp = client.post("/auth", data={"token": "token-xyz"}, follow_redirects=False)
    assert resp.status_code == HTTPStatus.FORBIDDEN


def test_auth_forbidden_invalid_token() -> None:
    pdf_state.inverse_search_enabled = True
    pdf_state.websocket_token = "correct-token"

    app = _make_app()
    client = TestClient(app)

    resp = client.post("/auth", data={"token": "wrong-token"}, follow_redirects=False)
    assert resp.status_code == HTTPStatus.SEE_OTHER
    assert "error=1" in resp.headers["location"]
