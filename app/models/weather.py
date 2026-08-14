from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WeatherReading(Base):
    __tablename__ = "weather_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str] = mapped_column(String, index=True)
    temperature_c: Mapped[float] = mapped_column(Float)
    wind_speed_ms: Mapped[float] = mapped_column(Float)
    solar_irradiance_wm2: Mapped[float] = mapped_column(Float)
