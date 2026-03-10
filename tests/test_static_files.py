"""Tests for src.routes.static_files.setup_static_files."""

from pathlib import Path

class DummyApp:
    def __init__(self):
        self.mounted = []

    def mount(self, path: str, app, name: str):
        self.mounted.append((path, name))


class DummySettings:
    def __init__(self, static_dir: Path):
        self.static_dir = static_dir


def test_setup_static_files_mounts_static(monkeypatch, tmp_path):
    app = DummyApp()
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "dummy.js").write_text("console.log('hi');")
    dummy_settings = DummySettings(static_dir=static_dir)
    monkeypatch.setattr("src.routes.static_files.get_settings", lambda: dummy_settings)

    from src.routes.static_files import setup_static_files
    setup_static_files(app)

    assert any(m[0] == "/static" for m in app.mounted)
