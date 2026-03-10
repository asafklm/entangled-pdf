"""Tests for src.websocket_monitor.WebSocketMonitor."""

import io
from src.websocket_monitor import WebSocketMonitor


def test_log_receive_writes_redacted_action():
    buf = io.StringIO()
    mon = WebSocketMonitor(output=buf)
    mon.enable()
    mon.log_receive({"action": "ping", "token": "secret"})
    out = buf.getvalue()
    assert "[RECV]" in out
    assert "action=ping" in out
    assert "token" not in out


def test_log_sent_writes_redacted_fields():
    buf = io.StringIO()
    mon = WebSocketMonitor(output=buf)
    mon.enable()
    mon.log_sent({"action": "synctex", "page": 3.0, "x": 10.0, "y": 20.0, "password": "secret"})
    out = buf.getvalue()
    assert "[SENT]" in out
    assert "action=synctex" in out
