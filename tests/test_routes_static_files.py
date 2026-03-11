from __future__ import annotations

from pathlib import Path
import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pdfserver.routes import static_files as static_files_module

class DummySettings:
    def __init__(self, static_dir: Path):
        self.static_dir = static_dir


def test_static_files_serves_file(monkeypatch, tmp_path: Path) -> None:
    # Prepare a temporary directory with a static file
    static_dir = tmp_path / "static_dir"
    static_dir.mkdir()
    (static_dir / "hello.txt").write_text("hello world")

    # Patch get_settings to return our dummy settings
    monkeypatch.setattr(static_files_module, "get_settings", lambda: type("S", (), {"static_dir": static_dir})())

    app = FastAPI()
    static_files_module.setup_static_files(app)
    client = TestClient(app)

    resp = client.get("/static/hello.txt")
    assert resp.status_code == 200
    assert resp.text == "hello world"
