import logging

import redis.asyncio as redis

from services.alert_auth.app.alerts import evaluate_reading
from services.alert_auth.app.db import SessionLocal
from services.alert_auth.app.models import Alert
from shared.events import ALERTS_CHANNEL, AlertEvent, IoTReadingEvent, parse_event

logger = logging.getLogger(__name__)


class AlertHandler:
    """Handles an IoT reading event: evaluates alert rules and publishes any alerts."""

    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client

    async def __call__(self, body: bytes) -> None:
        event = parse_event(body)
        if not isinstance(event, IoTReadingEvent):
            return

        payload = event.payload
        async with SessionLocal() as session:
            alerts = await evaluate_reading(session, payload.device_id, payload.power_kw)

        for alert in alerts:
            await self._publish(alert)

    async def _publish(self, alert: Alert) -> None:
        event = AlertEvent(
            alert_id=alert.id,
            device_id=alert.device_id,
            rule_id=alert.rule_id,
            message=alert.message,
            power_kw=alert.power_kw,
            threshold=alert.threshold,
            acknowledged=alert.acknowledged,
        )
        await self._redis.publish(ALERTS_CHANNEL, event.model_dump_json())
        logger.info("Published alert %d for device %s", alert.id, alert.device_id)
