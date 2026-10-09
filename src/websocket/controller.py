import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .manager import ws_manager

logger = logging.getLogger("oasis_backend.websocket")

router = APIRouter(
    prefix="/ws",
    tags=["WebSockets"]
)


@router.websocket("/admin")
async def admin_websocket_endpoint(websocket: WebSocket):
    """
    Real-time duplex WebSocket channel for Oasis Admin & staff dashboard.
    Emits instant alerts for:
      - NEW_ORDER
      - ORDER_STATUS_UPDATED
      - NEW_RESERVATION
      - NEW_NOTIFICATION
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to Oasis Realtime Event Bus"
        })
        while True:
            # Keep listening for client heartbeats/pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        ws_manager.disconnect(websocket)
