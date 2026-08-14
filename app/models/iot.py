from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class IoTReading(Base):
    __tablename__ = "iot_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    power_kw: Mapped[float] = mapped_column(Float)
    voltage_v: Mapped[float] = mapped_column(Float)
