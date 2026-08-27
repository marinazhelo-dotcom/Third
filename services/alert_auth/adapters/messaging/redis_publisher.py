import logging

import redis.asyncio as redis

from shared.events import ALERTS_CHANNEL
from services.alert_auth.domain.ports import AlertPublisher

logger = logging.getLogger(__name__)


class RedisAlertPublisher(AlertPublisher):
    """Publishes alert events to Redis pub/sub for real-time WebSocket delivery."""

    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client

    async def publish_alert(self, event: dict) -> None:
        import json

        await self._redis.publish(ALERTS_CHANNEL, json.dumps(event))
        logger.info("Published alert event to %s", ALERTS_CHANNEL)
