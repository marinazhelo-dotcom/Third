from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MarketPrice(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    timestamp: datetime
    region: str
    price_per_kwh: float
    currency: str
