import logging
from datetime import datetime, timedelta, timezone

from services.alert_auth.domain.models import Alert, AlertRule
from services.alert_auth.domain.ports import AlertRepository, AlertRuleRepository

logger = logging.getLogger(__name__)

COOLDOWN_SECONDS = 60


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def evaluate_reading(
    rule_repo: AlertRuleRepository,
    alert_repo: AlertRepository,
    device_id: str,
    power_kw: float,
    cooldown_seconds: int = COOLDOWN_SECONDS,
) -> list[Alert]:
    """Domain rule: create alerts for any enabled rules the reading breaches (with a cooldown).

    This is pure business logic — no framework imports.
    """
    rules = await rule_repo.list_enabled_for_device(device_id)

    now = datetime.now(timezone.utc)
    # timedelta here because this will be campared to datetime
    cooldown = timedelta(seconds=cooldown_seconds)
    triggered: list[Alert] = []

    for rule in rules:
        if power_kw <= rule.threshold:
            continue
        if rule.last_alert_at is not None \
        and now - _ensure_aware(rule.last_alert_at) < cooldown:
            continue

        alert = Alert(
            device_id=device_id,
            rule_id=rule.id,
            message=f"{device_id} power {power_kw:.2f} kW exceeds threshold {rule.threshold:.2f} kW",
            power_kw=power_kw,
            threshold=rule.threshold,
        )
        alert = await alert_repo.create(alert)
        await rule_repo.touch_last_alert(rule.id)
        triggered.append(alert)

    if triggered:
        logger.info("Raised %d alert(s) for device %s", len(triggered), device_id)

    return triggered
