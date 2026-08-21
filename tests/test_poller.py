import httpx
import pytest
import respx
from sqlalchemy import select

from app.config import AppConfig, BreakerConfig, RetryConfig, SourceConfig
from app.models import IoTReading, DB_SOURCE_MODELS
from app.poller import Poller
from app.sources.factory import get_source


def make_config(
    sources: list[SourceConfig],
    breaker: BreakerConfig | None = None,
    retry: RetryConfig | None = None,
) -> AppConfig:
    return AppConfig(
        breaker=breaker or BreakerConfig(failure_threshold=3),
        retry=retry or RetryConfig(max_attempts=2, base_delay_seconds=0.001),
        sources=sources,
    )


def iot_source(url: str = "http://iot.test/data") -> SourceConfig:
    return SourceConfig(name="iot", type="iot", url=url, interval_seconds=5)


async def test_poll_once_stores_readings(monkeypatch, session_factory):
    monkeypatch.setattr("app.poller.SessionLocal", session_factory)
    poller = Poller(make_config([iot_source()]))
    source = poller.config.sources[0]
    provider = get_source(source, poller._client)
    breaker = poller.breaker_for("iot")
    model_cls = DB_SOURCE_MODELS["iot"]

    with respx.mock:
        respx.get("http://iot.test/data").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "device_id": "solar-1",
                        "timestamp": "2026-01-01T00:00:00+00:00",
                        "power_kw": 1.5,
                        "voltage_v": 230.0,
                    }
                ],
            )
        )
        await poller._poll_once(source, provider, breaker, model_cls)

    assert breaker.state.value == "closed"
    async with session_factory() as session:
        rows = (await session.execute(select(IoTReading))).scalars().all()
        assert len(rows) == 1
        assert rows[0].device_id == "solar-1"
    await poller.stop()


async def test_poll_once_retries_then_trips_breaker(monkeypatch, session_factory):
    monkeypatch.setattr("app.poller.SessionLocal", session_factory)
    config = make_config(
        [iot_source()], breaker=BreakerConfig(failure_threshold=2, cooldown_seconds=60)
    )
    poller = Poller(config)
    source = config.sources[0]
    provider = get_source(source, poller._client)
    breaker = poller.breaker_for("iot")
    model_cls = DB_SOURCE_MODELS["iot"]

    with respx.mock:
        respx.get("http://iot.test/data").mock(return_value=httpx.Response(500))

        await poller._poll_once(source, provider, breaker, model_cls)
        assert breaker.state.value == "closed"
        assert breaker.failure_count == 1

        await poller._poll_once(source, provider, breaker, model_cls)
        assert breaker.state.value == "open"

    await poller.stop()


async def test_poll_once_skips_when_open(monkeypatch, session_factory):
    monkeypatch.setattr("app.poller.SessionLocal", session_factory)
    config = make_config(
        [iot_source()], breaker=BreakerConfig(failure_threshold=1, cooldown_seconds=60)
    )
    poller = Poller(config)
    source = config.sources[0]
    provider = get_source(source, poller._client)
    breaker = poller.breaker_for("iot")
    model_cls = DB_SOURCE_MODELS["iot"]

    breaker.record_failure()
    assert breaker.state.value == "open"

    with respx.mock:
        route = respx.get("http://iot.test/data").mock(
            return_value=httpx.Response(200, json=[])
        )
        await poller._poll_once(source, provider, breaker, model_cls)

    assert route.call_count == 0
    await poller.stop()
