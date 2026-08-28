from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class User:
    id: int = 0
    username: str = ""
    password_hash: str = ""
    role: str = "viewer"  # admin | operator | viewer


@dataclass
class AlertRule:
    id: int = 0
    device_id: str = ""
    threshold: float = 0.0
    enabled: bool = True
    last_alert_at: datetime | None = None


@dataclass
class Alert:
    id: int = 0
    device_id: str = ""
    rule_id: int = 0
    message: str = ""
    power_kw: float = 0.0
    threshold: float = 0.0
    created_at: datetime = field(default_factory=_utcnow)
    acknowledged: bool = False
    acknowledged_by: str | None = None
