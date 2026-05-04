"""Browser FastAPI application for TCP + HTTPS transport.

Provides browser-facing endpoints including viewer, WebSocket,
static files, and state polling.
"""

from fastapi import FastAPI

from entangledpdf.routes import auth, pdf, state, static_files, view, websocket

app = FastAPI(title="EntangledPdf Browser")

# Browser-facing routes
app.include_router(auth.router)
app.include_router(view.router)
app.include_router(pdf.router)
app.include_router(state.router)  # Also available on admin app
app.include_router(websocket.router)

# Setup static files
static_files.setup_static_files(app)
