import json
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

# RabbitMQ topic exchange: events are published here and routed to queues by routing key.
EVENTS_EXCHANGE = "energy.events"

# RabbitMQ queue the Telemetry service consumes IoT events from.
TELEMETRY_IOT_QUEUE = "telemetry.iot.readings"

# Redis pub/sub channels (subscribed by the UI via WebSocket).
TELEMETRY_LIVE_CHANNEL = "telemetry.live"
ALERTS_CHANNEL = "alerts"

# Event type names (each source publishes a distinct type).
IOT_READING_TYPE = "iot.reading"
WEATHER_READING_TYPE = "weather.reading"
MARKET_PRICE_TYPE = "market.price"

EVENT_TYPES: dict[str, str] = {
    "iot": IOT_READING_TYPE,
    "weather": WEATHER_READING_TYPE,
    "market": MARKET_PRICE_TYPE,
}

ROUTING_KEYS: dict[str, str] = {
    "iot": "telemetry.iot",
    "weather": "weather.reading",
    "market": "market.price",
}


class ReadingEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    source: str
    produced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any]


class IoTReadingPayload(BaseModel):
    device_id: str
    timestamp: datetime
    power_kw: float
    voltage_v: float


class IoTReadingEvent(ReadingEvent):
    type: Literal["iot.reading"] = IOT_READING_TYPE
    source: Literal["iot"] = "iot"
    payload: IoTReadingPayload


class AlertEvent(BaseModel):
    """An alert raised when a reading breaches a rule, published to Redis for the UI."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["alert"] = "alert"
    produced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    alert_id: int
    device_id: str
    rule_id: int
    message: str
    power_kw: float
    threshold: float
    acknowledged: bool = False


def make_reading_event(source: str, reading: dict[str, Any]) -> ReadingEvent:
    return ReadingEvent(
        type=EVENT_TYPES.get(source, f"{source}.reading"),
        source=source,
        payload=reading,
    )


def parse_event(body: bytes) -> ReadingEvent:
    raw = json.loads(body)
    if raw.get("type") == IOT_READING_TYPE:
        return IoTReadingEvent.model_validate(raw)
    return ReadingEvent.model_validate(raw)
