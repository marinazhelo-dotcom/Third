import structlog

from services.telemetry.app.cache import Cache
from services.telemetry.app.db import SessionLocal
from services.telemetry.app.models import Reading
from shared.events import IoTReadingEvent, parse_event
from shared.metrics import TELEMETRY_EVENTS_CONSUMED_TOTAL, TELEMETRY_READINGS_STORED_TOTAL

logger = structlog.get_logger()


class EventHandler:
    """Handles a raw event body: parses it, persists to PostgreSQL, and updates Redis."""

    def __init__(self, cache: Cache):
        self._cache = cache

    async def __call__(self, body: bytes) -> None:
        """Persist IoT readings to the DB, then refresh the cache and publish live."""
        event = parse_event(body)
        if not isinstance(event, IoTReadingEvent):
            logger.info("event_ignored", event_type=event.type)
            return

        payload = event.payload
        async with SessionLocal() as session:
            session.add(
                Reading(
                    device_id=payload.device_id,
                    timestamp=payload.timestamp,
                    power_kw=payload.power_kw,
                    voltage_v=payload.voltage_v,
                )
            )
            await session.commit()

        reading = payload.model_dump(mode="json")
        await self._cache.set_latest(payload.device_id, reading)
        await self._cache.publish_live(reading)
        TELEMETRY_EVENTS_CONSUMED_TOTAL.inc()
        TELEMETRY_READINGS_STORED_TOTAL.inc()
        logger.debug("event_handled", event_id=event.event_id, device_id=payload.device_id)
