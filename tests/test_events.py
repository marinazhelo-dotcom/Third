from datetime import datetime, timezone

from shared.events import (
    IoTReadingEvent,
    make_reading_event,
    parse_event,
)


def test_make_reading_event_sets_type_and_routing_info():
    reading = {
        "device_id": "solar-1",
        "timestamp": datetime.now(timezone.utc),
        "power_kw": 1.5,
        "voltage_v": 230.0,
    }
    event = make_reading_event("iot", reading)
    assert event.type == "iot.reading"
    assert event.source == "iot"
    assert event.payload["device_id"] == "solar-1"


def test_parse_event_roundtrips_to_typed_event():
    reading = {
        "device_id": "solar-1",
        "timestamp": datetime.now(timezone.utc),
        "power_kw": 1.5,
        "voltage_v": 230.0,
    }
    body = make_reading_event("iot", reading).model_dump_json().encode()

    event = parse_event(body)
    assert isinstance(event, IoTReadingEvent)
    assert event.payload.device_id == "solar-1"
    assert isinstance(event.payload.timestamp, datetime)
    assert event.payload.power_kw == 1.5


def test_parse_event_non_iot_stays_generic():
    body = make_reading_event("weather", {"location": "berlin"}).model_dump_json().encode()

    event = parse_event(body)
    assert not isinstance(event, IoTReadingEvent)
    assert event.type == "weather.reading"
