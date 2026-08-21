# executed (once) when the module is imported

from app.models.iot import IoTReading
from app.models.market import MarketPrice
from app.models.weather import WeatherReading

from app.db import Base

DB_SOURCE_MODELS: dict[str, type[Base]] = {
    "iot": IoTReading,
    "weather": WeatherReading,
    "market": MarketPrice,
}

# When import *, Python imports only the names listed in __all__ 
# Without __all__, import * grabs every public name (everything not starting with _).
__all__ = ["IoTReading", "MarketPrice", "WeatherReading", "DB_SOURCE_MODELS"]
