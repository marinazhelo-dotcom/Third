import json

import redis.asyncio as redis
import structlog

from shared.events import ALERTS_CHANNEL
from services.alert_auth.domain.ports import AlertPublisher

logger = structlog.get_logger()


class RedisAlertPublisher(AlertPublisher):
    """Publishes alert events to Redis pub/sub for real-time WebSocket delivery."""

    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client

    async def publish_alert(self, event: dict) -> None:
        await self._redis.publish(ALERTS_CHANNEL, json.dumps(event))
        logger.info("alert_published_to_redis", channel=ALERTS_CHANNEL, alert_id=event.get("alert_id"))
