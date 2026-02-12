import argparse
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from typing import Set
from pathlib import Path

app = FastAPI()
SHARED_SECRET = "super-secret-123"
CONFIG = {}

# --- BROADCAST MANAGER ---
class ConnectionManager:
    def __init__(self):
        # A set stores unique active connections
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # Send to every single connected client
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass # Handle stale connections gracefully

manager = ConnectionManager()

# --- ROUTES ---

@app.get("/view", response_class=HTMLResponse)
async def view_page():
    html_content = Path("pdf_server.html").read_text()
    return html_content.replace("{{PORT}}", str(CONFIG['port']))

@app.get("/get-pdf")
async def get_pdf():
    return FileResponse(CONFIG['pdf_file'], headers={"page": "1"}, media_type="application/pdf")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep-alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Global state
CONFIG = {"current_page": 1} 

@app.get("/current-state")
async def get_state():
    return {"page": CONFIG["current_page"]}

@app.post("/webhook/update")


@app.post("/webhook/update")
async def receive_webhook(data: dict, x_api_key: str = Header(None)):
    if x_api_key != SHARED_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    page_number = data.get("page", 1)
    CONFIG["current_page"] = page_number # Store the state
    # Broadcast to EVERYONE
    await manager.broadcast({"action": "reload", "page": page_number})
    return {
        "status": "success", 
        "broadcast_to": len(manager.active_connections),
        "page": page_number
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_file")
    parser.add_argument("port_arg")
    args = parser.parse_args()
    
    port = int(args.port_arg.split('=')[1])
    CONFIG['pdf_file'] = args.pdf_file
    CONFIG['port'] = port
    
    uvicorn.run(app, host="0.0.0.0", port=port)

