from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from typing import Dict
import uvicorn

app = FastAPI()

# Configuration
SHARED_SECRET = "super-secret-123"

# 1. Connection Manager: Keeps track of which Browser is connected to which User
class ConnectionManager:
    def __init__(self):
        # Dictionary to store {user_id: websocket_connection}
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"Browser connected: User {user_id}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"Browser disconnected: User {user_id}")

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
            return True
        return False

manager = ConnectionManager()

# 2. BROWSER SIDE: The WebSocket endpoint the browser connects to
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            # We just wait for the browser to stay connected
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id)

# 3. PROCESS SIDE: The Local Webhook the external process hits
@app.post("/webhook/update")
async def receive_webhook(data: dict, x_api_key: str = Header(None)):
    # Security check
    if x_api_key != SHARED_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Secret")

    user_id = data.get("user_id")
    content = data.get("content")

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required")

    # Try to push the data to the browser
    delivered = await manager.send_to_user(user_id, {"update": content})
    
    return {
        "status": "received", 
        "delivered_to_browser": delivered
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
    # uvicorn.run(app, host="127.0.0.1", port=8001)

