from typing import List, Dict
from fastapi import WebSocket
import asyncio

class ConnectionManager:
    def __init__(self):
        # Map site_id -> List of WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, site_id: str):
        await websocket.accept()
        if site_id not in self.active_connections:
            self.active_connections[site_id] = []
        self.active_connections[site_id].append(websocket)
        print(f"Client connected to site {site_id}. Total clients: {len(self.active_connections[site_id])}")

    def disconnect(self, websocket: WebSocket, site_id: str):
        if site_id in self.active_connections:
            if websocket in self.active_connections[site_id]:
                self.active_connections[site_id].remove(websocket)
            if not self.active_connections[site_id]:
                del self.active_connections[site_id]
        print(f"Client disconnected from site {site_id}")

    async def broadcast(self, message: dict, site_id: str):
        if site_id in self.active_connections:
            # Iterate over a copy to avoid modification issues during iteration if disconnect happens
            for connection in self.active_connections[site_id][:]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error sending message to client: {e}")
                    # Cleanup dead connection
                    self.disconnect(connection, site_id)

manager = ConnectionManager()
