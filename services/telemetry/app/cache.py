import json

import redis.asyncio as redis

from services.telemetry.app.config import get_settings
from shared.events import TELEMETRY_LIVE_CHANNEL


class Cache:
    """Redis-backed store of the one latest reading per device, plus live pub/sub."""

    def __init__(self, url: str):
        self._client = redis.from_url(url, decode_responses=True)

    def _key(self, device_id: str) -> str:
        return f"device:{device_id}:latest"

    async def set_latest(self, device_id: str, reading: dict) -> None:
        """Store the latest reading for a device (as JSON) under its cache key."""
        await self._client.set(self._key(device_id), json.dumps(reading, default=str))

    async def get_latest(self, device_id: str) -> dict | None:
        """Return the latest cached reading for a device, or None if absent."""
        raw = await self._client.get(self._key(device_id))
        return json.loads(raw) if raw else None

    async def publish_live(self, reading: dict) -> None:
        """Publish a reading to the live telemetry channel (pub/sub)."""
        await self._client.publish(TELEMETRY_LIVE_CHANNEL, json.dumps(reading, default=str))

    async def close(self) -> None:
        await self._client.aclose()


def build_cache() -> Cache:
    return Cache(get_settings().redis_url)
