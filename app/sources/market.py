from app.schemas.market import MarketPrice
from app.sources.base import SourceProvider


class MarketProvider(SourceProvider[MarketPrice]):
    async def fetch(self) -> list[MarketPrice]:
        resp = await self._client.get(self._url)
        resp.raise_for_status()
        return [MarketPrice(**item) for item in resp.json()]
