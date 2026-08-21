from app.schemas.iot import IoTReading
from app.sources.base import SourceProvider


# [IoTReading] goes into T in SourceProvider
class IoTProvider(SourceProvider[IoTReading]):
    
    async def fetch(self) -> list[IoTReading]:
        resp = await self._client.get(self._url)
        resp.raise_for_status()
        return [IoTReading(**item) for item in resp.json()]
