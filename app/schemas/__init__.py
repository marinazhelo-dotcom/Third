from pydantic import BaseModel

from app.schemas.iot import IoTReading
from app.schemas.market import MarketPrice
from app.schemas.weather import WeatherReading

API_SOURCE_SCHEMAS: dict[str, type[BaseModel]] = {
    "iot": IoTReading,
    "weather": WeatherReading,
    "market": MarketPrice,
}

__all__ = ["IoTReading", "MarketPrice", "WeatherReading", "API_SOURCE_SCHEMAS"]
