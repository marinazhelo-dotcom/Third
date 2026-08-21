import json
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

EXCHANGE = "energy.events"

QUEUE_TELEMETRY_IOT = "telemetry.iot.readings"

EVENT_TYPES: dict[str, str] = {
    "iot": "iot.reading",
    "weather": "weather.reading",
    "market": "market.price",
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
    type: Literal["iot.reading"] = "iot.reading"
    source: Literal["iot"] = "iot"
    payload: IoTReadingPayload


def make_reading_event(source: str, reading: dict[str, Any]) -> ReadingEvent:
    return ReadingEvent(
        type=EVENT_TYPES.get(source, f"{source}.reading"),
        source=source,
        payload=reading,
    )


def parse_event(body: bytes) -> ReadingEvent:
    raw = json.loads(body)
    if raw.get("type") == "iot.reading":
        return IoTReadingEvent.model_validate(raw)
    return ReadingEvent.model_validate(raw)
