import json

import redis.asyncio as redis

from services.telemetry.app.config import get_settings

LIVE_CHANNEL = "telemetry.live"


class Cache:
    def __init__(self, url: str):
        self._client = redis.from_url(url, decode_responses=True)

    def _key(self, device_id: str) -> str:
        return f"device:{device_id}:latest"

    async def set_latest(self, device_id: str, reading: dict) -> None:
        await self._client.set(self._key(device_id), json.dumps(reading, default=str))

    async def get_latest(self, device_id: str) -> dict | None:
        raw = await self._client.get(self._key(device_id))
        return json.loads(raw) if raw else None

    async def publish_live(self, reading: dict) -> None:
        await self._client.publish(LIVE_CHANNEL, json.dumps(reading, default=str))

    async def close(self) -> None:
        await self._client.aclose()


def build_cache() -> Cache:
    return Cache(get_settings().redis_url)
