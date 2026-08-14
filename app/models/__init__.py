from app.models.iot import IoTReading
from app.models.market import MarketPrice
from app.models.weather import WeatherReading

SOURCE_MODELS: dict[str, type] = {
    "iot": IoTReading,
    "weather": WeatherReading,
    "market": MarketPrice,
}

__all__ = ["IoTReading", "MarketPrice", "WeatherReading", "SOURCE_MODELS"]
