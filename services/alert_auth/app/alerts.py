import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.alert_auth.app.config import get_settings
from services.alert_auth.app.models import Alert, AlertRule

logger = logging.getLogger(__name__)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def evaluate_reading(session: AsyncSession, device_id: str, power_kw: float) -> list[Alert]:
    """Create alerts for any enabled rules the reading breaches (with a cooldown)."""
    result = await session.execute(
        select(AlertRule).where(
            AlertRule.device_id == device_id, AlertRule.enabled.is_(True)
        )
    )
    rules = result.scalars().all()

    now = datetime.now(timezone.utc)
    cooldown = timedelta(seconds=get_settings().alert_cooldown_seconds)
    triggered: list[Alert] = []

    for rule in rules:
        if power_kw <= rule.threshold:
            continue
        if rule.last_alert_at is not None and now - _ensure_aware(rule.last_alert_at) < cooldown:
            continue

        alert = Alert(
            device_id=device_id,
            rule_id=rule.id,
            message=f"{device_id} power {power_kw:.2f} kW exceeds threshold {rule.threshold:.2f} kW",
            power_kw=power_kw,
            threshold=rule.threshold,
        )
        session.add(alert)
        rule.last_alert_at = now
        triggered.append(alert)

    if triggered:
        await session.commit()
        logger.info("Raised %d alert(s) for device %s", len(triggered), device_id)

    return triggered
