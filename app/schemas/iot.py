from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IoTReading(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    # from_attributes=True means that the config will be created from attributes, not dict

    id: int | None = None
    device_id: str
    timestamp: datetime
    power_kw: float
    voltage_v: float
