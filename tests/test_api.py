from datetime import datetime, timezone

import httpx
import pytest

from app.circuit_breaker import CircuitBreaker
from app.db import get_session
from app.main import app
from app.models import IoTReading


@pytest.fixture
async def client(session_factory):
    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_readings_unknown_source(client):
    resp = await client.get("/readings/nope")
    assert resp.status_code == 404


async def test_readings_returns_rows(client, session_factory):
    async with session_factory() as session:
        session.add(
            IoTReading(
                device_id="solar-1",
                timestamp=datetime.now(timezone.utc),
                power_kw=1.0,
                voltage_v=230.0,
            )
        )
        await session.commit()

    resp = await client.get("/readings/iot")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["device_id"] == "solar-1"
    assert data[0]["id"] == 1


async def test_status(client):
    class FakePoller:
        def breakers(self):
            return {"iot": CircuitBreaker(failure_threshold=2)}

    app.state.poller = FakePoller()
    resp = await client.get("/status")
    assert resp.status_code == 200
    assert resp.json() == {"iot": {"state": "closed", "failure_count": 0}}
