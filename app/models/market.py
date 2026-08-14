from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    region: Mapped[str] = mapped_column(String, index=True)
    price_per_kwh: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String)
