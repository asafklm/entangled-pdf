import argparse
import html
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from typing import Set
from pathlib import Path

app = FastAPI()
SHARED_SECRET = "super-secret-123"

# Global Configuration & State
CONFIG = {
    "pdf_file": "",
    "port": 8001,
    "current_page": 1  
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
    return {"page": CONFIG["current_page"]}

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
    if x_api_key != SHARED_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    page = int(data.get("page", 1))
    CONFIG["current_page"] = page  # Update the global state
    
    await manager.broadcast({"action": "reload", "page": page})
    return {"status": "success", "current_page": page}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_file")
    parser.add_argument("port_arg")
    args = parser.parse_args()
    
    CONFIG['port'] = int(args.port_arg.split('=')[1])
    CONFIG['pdf_file'] = args.pdf_file
    
    uvicorn.run(app, host="0.0.0.0", port=CONFIG['port'])

