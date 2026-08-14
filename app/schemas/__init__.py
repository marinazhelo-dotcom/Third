from app.schemas.iot import IoTReading
from app.schemas.market import MarketPrice
from app.schemas.weather import WeatherReading

SOURCE_SCHEMAS: dict[str, type] = {
    "iot": IoTReading,
    "weather": WeatherReading,
    "market": MarketPrice,
}

__all__ = ["IoTReading", "MarketPrice", "WeatherReading", "SOURCE_SCHEMAS"]
