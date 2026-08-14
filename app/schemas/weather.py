from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WeatherReading(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    timestamp: datetime
    location: str
    temperature_c: float
    wind_speed_ms: float
    solar_irradiance_wm2: float
