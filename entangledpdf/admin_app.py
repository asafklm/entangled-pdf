"""Admin FastAPI application for Unix socket transport.

Provides API endpoints accessible only via Unix domain socket.
No API key authentication required - transport-level security via
filesystem permissions (socket mode 0600, directory 0700).
"""

from fastapi import FastAPI, Request

from entangledpdf.routes import load_pdf, webhook, state

app = FastAPI(title="EntangledPdf Admin")


@app.middleware("http")
async def mark_unix_socket_transport(request: Request, call_next):
    """Mark requests as coming from Unix socket transport.
    
    This allows routes to skip API key authentication when
    the request comes through the Unix socket.
    """
    request.state.unix_socket = True
    response = await call_next(request)
    return response


# Admin-only routes (Unix socket transport)
# API key checks are skipped when request.state.unix_socket is True
app.include_router(load_pdf.router)
app.include_router(webhook.router)
app.include_router(state.router)
