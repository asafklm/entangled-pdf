import argparse
import html
import os
import time
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from typing import Set
from pathlib import Path

app = FastAPI()
SHARED_SECRET = os.getenv("PDF_SERVER_SECRET", "super-secret-123")

# Global Configuration & State
CONFIG = {
    "pdf_file": "",
    "port": int(os.getenv("PDF_SERVER_PORT", "8431")),
    "current_page": 1,
    "current_y": None,
    "last_update_time": 0  # Timestamp of last broadcast
}

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.get("/view", response_class=HTMLResponse)
async def view_page():
    html_content = Path("pdf_server.html").read_text()
    html_content = html_content.replace("{{PORT}}", html.escape(str(CONFIG['port'])))
    html_content = html_content.replace("{{FILENAME}}", html.escape(str(CONFIG['pdf_file'])))
    return html_content

@app.get("/get-pdf")
async def get_pdf():
    return FileResponse(CONFIG['pdf_file'], media_type="application/pdf")

@app.get("/current-state")
async def get_state():
    """Endpoint for the iPad to call when it refocuses"""
    return {
        "page": CONFIG["current_page"],
        "y": CONFIG["current_y"],
        "last_update_time": CONFIG["last_update_time"]
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/webhook/update")
async def receive_webhook(data: dict, x_api_key: str = Header(None)):
    """Receive page updates and SyncTeX forward search coordinates"""
    if x_api_key != SHARED_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    page = int(data.get("page", 1))
    x = data.get("x")  # Optional: PDF x coordinate from synctex
    y = data.get("y")  # Optional: PDF y coordinate from synctex
    
    CONFIG["current_page"] = page
    CONFIG["current_y"] = y  # Store y for refocus
    CONFIG["last_update_time"] = int(time.time() * 1000)  # Current timestamp in milliseconds
    
    # Always broadcast as synctex (coordinates optional)
    await manager.broadcast({
        "action": "synctex",
        "page": page,
        "x": x,
        "y": y,
        "timestamp": CONFIG["last_update_time"]
    })
    
    return {"status": "success", "page": page, "x": x, "y": y}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_file")
    parser.add_argument("port_arg", nargs="?", help="Port in format port=8001 (optional, defaults to PDF_SERVER_PORT env var or 8001)")
    args = parser.parse_args()
    
    if args.port_arg:
        CONFIG['port'] = int(args.port_arg.split('=')[1])
    CONFIG['pdf_file'] = args.pdf_file
    
    uvicorn.run(app, host="0.0.0.0", port=CONFIG['port'])

