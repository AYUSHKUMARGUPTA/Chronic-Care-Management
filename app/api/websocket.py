from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Simple in-memory set of active WebSocket connections (per-process)
active_connections: Set[WebSocket] = set()


@router.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            # keep the connection alive; clients may send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.discard(websocket)


async def broadcast_alert_async(payload: dict) -> None:
    """Send an alert payload to all connected websockets (best-effort)."""
    disconnects: list[WebSocket] = []
    for conn in list(active_connections):
        try:
            await conn.send_json(payload)
        except Exception:
            disconnects.append(conn)

    for d in disconnects:
        active_connections.discard(d)


def broadcast_alert_sync(payload: dict) -> None:
    """Compatibility wrapper so synchronous code can trigger broadcasts via task scheduling.

    Note: Use FastAPI background tasks to schedule the `broadcast_alert` coroutine.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        # schedule but don't await
        loop.create_task(broadcast_alert_async(payload))
    except RuntimeError:
        # no running loop; ignore
        pass


# Expose a simple API for other modules to call; choose sync wrapper for simplicity
def broadcast_alert(payload: dict) -> None:
    broadcast_alert_sync(payload)
