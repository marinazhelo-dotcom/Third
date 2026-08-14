import httpx
import pytest

from app.config import SourceConfig
from app.sources.factory import get_source
from app.sources.iot import IoTProvider
from app.sources.market import MarketProvider
from app.sources.weather import WeatherProvider


def make_source(type_: str) -> SourceConfig:
    return SourceConfig(name=type_, type=type_, url="http://x.test", interval_seconds=5)


async def test_factory_maps_types():
    client = httpx.AsyncClient()
    try:
        assert isinstance(get_source(make_source("iot"), client), IoTProvider)
        assert isinstance(get_source(make_source("weather"), client), WeatherProvider)
        assert isinstance(get_source(make_source("market"), client), MarketProvider)
    finally:
        await client.aclose()


async def test_factory_unknown_type_raises():
    client = httpx.AsyncClient()
    try:
        with pytest.raises(ValueError):
            get_source(make_source("nope"), client)
    finally:
        await client.aclose()
