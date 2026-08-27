import asyncio
import json
import logging

import redis.asyncio as redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.alert_auth.adapters.security.jwt import PyJWTTokenService
from services.alert_auth.infrastructure.config import get_settings
from shared.events import ALERTS_CHANNEL, TELEMETRY_LIVE_CHANNEL

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Tracks open WebSocket clients and broadcasts messages to all of them."""

    def __init__(self):
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, channel: str, data: str) -> None:
        payload = json.dumps({"channel": channel, "data": json.loads(data)})
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.discard(ws)


manager = ConnectionManager()


async def redis_subscriber(redis_url: str) -> None:
    """Subscribe to Redis pub/sub channels and fan messages out to WebSocket clients."""
    client = redis.from_url(redis_url, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(TELEMETRY_LIVE_CHANNEL, ALERTS_CHANNEL)
    async for message in pubsub.listen():
        if message["type"] == "message":
            await manager.broadcast(message["channel"], message["data"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Authenticate via ?token=, then stream live telemetry + alerts to the client."""
    token = websocket.query_params.get("token")
    if token is None:
        await websocket.close(code=1008)
        return
    try:
        user = PyJWTTokenService().decode_token(token)
    except Exception:
        await websocket.close(code=1008)
        return

    logger.info("WS connected: user %s (%s)", user.get("sub"), user.get("role"))
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
