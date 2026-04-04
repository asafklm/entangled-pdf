"""Routes package initialization.

Exports all route modules for easy importing.
"""

from entangledpdf.routes import pdf, state, static_files, view, webhook, websocket

__all__ = ["view", "pdf", "state", "webhook", "websocket", "static_files"]
