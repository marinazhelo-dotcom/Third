from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.telemetry.app.db import Base
from services.telemetry.app.handler import EventHandler
from services.telemetry.app.models import Reading
from shared.events import make_reading_event


class FakeCache:
    """In-memory stand-in for the Redis cache (latest + pub/sub)."""

    def __init__(self):
        self.latest: dict[str, dict] = {}
        self.published: list[dict] = []

    async def set_latest(self, device_id: str, reading: dict) -> None:
        self.latest[device_id] = reading

    async def publish_live(self, reading: dict) -> None:
        self.published.append(reading)


@pytest.fixture
async def engine(tmp_path):
    db_path = tmp_path / "telemetry.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


def make_iot_event_body() -> bytes:
    """Serialize an IoT reading event to JSON bytes."""
    event = make_reading_event(
        "iot",
        {
            "device_id": "solar-1",
            "timestamp": datetime.now(timezone.utc),
            "power_kw": 1.5,
            "voltage_v": 230.0,
        },
    )
    return event.model_dump_json().encode()


async def test_handler_stores_iot_event(monkeypatch, session_factory):
    """An IoT event is persisted to the DB and pushed to the cache + pub/sub."""
    monkeypatch.setattr("services.telemetry.app.handler.SessionLocal", session_factory)
    cache = FakeCache()
    handler = EventHandler(cache)

    await handler(make_iot_event_body())

    async with session_factory() as session:
        rows = (await session.execute(select(Reading))).scalars().all()
        assert len(rows) == 1
        assert rows[0].device_id == "solar-1"
        assert rows[0].power_kw == 1.5

    assert cache.latest["solar-1"]["device_id"] == "solar-1"
    assert len(cache.published) == 1


async def test_handler_ignores_non_iot_event(monkeypatch, session_factory):
    """Non-IoT events are ignored: nothing persisted, nothing cached."""
    monkeypatch.setattr("services.telemetry.app.handler.SessionLocal", session_factory)
    cache = FakeCache()
    handler = EventHandler(cache)

    body = make_reading_event("weather", {"location": "berlin"}).model_dump_json().encode()
    await handler(body)

    async with session_factory() as session:
        rows = (await session.execute(select(Reading))).scalars().all()
        assert len(rows) == 0

    assert cache.latest == {}
    assert cache.published == []
