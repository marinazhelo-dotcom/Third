import httpx

from app.config import SourceConfig
from app.sources.base import SourceProvider
from app.sources.iot import IoTProvider
from app.sources.market import MarketProvider
from app.sources.weather import WeatherProvider

_PROVIDERS: dict[str, type[SourceProvider]] = {
    "iot": IoTProvider,
    "weather": WeatherProvider,
    "market": MarketProvider,
}


def get_source(config: SourceConfig, client: httpx.AsyncClient) -> SourceProvider:
    try:
        provider_cls = _PROVIDERS[config.type]
    except KeyError:
        raise ValueError(f"Unknown source type: {config.type!r}") from None
    return provider_cls(client=client, url=config.url)
