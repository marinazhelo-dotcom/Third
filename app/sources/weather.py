from app.schemas.weather import WeatherReading
from app.sources.base import SourceProvider


class WeatherProvider(SourceProvider[WeatherReading]):
    async def fetch(self) -> list[WeatherReading]:
        resp = await self._client.get(self._url)
        resp.raise_for_status()
        return [WeatherReading(**item) for item in resp.json()]
