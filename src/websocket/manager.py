import json
import logging
import asyncio
from typing import Set, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("oasis_backend.websocket")


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Admin WebSocket connected. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"Admin WebSocket disconnected. Total active: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        if not self.active_connections:
            return

        payload = {
            "type": event_type,
            "data": data,
        }
        message_text = json.dumps(payload, default=str)
        dead_connections = []

        for connection in list(self.active_connections):
            try:
                await connection.send_text(message_text)
            except Exception as e:
                logger.warning(f"Error sending to WebSocket client: {e}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    def broadcast_sync(self, event_type: str, data: Dict[str, Any]):
        """Synchronous wrapper so regular FastAPI/SQLAlchemy services can trigger broadcasts."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(event_type, data))
        except RuntimeError:
            try:
                asyncio.run(self.broadcast(event_type, data))
            except Exception as e:
                logger.error(f"Failed to broadcast websocket event: {e}")


ws_manager = ConnectionManager()
