import structlog

from services.alert_auth.domain.ports import AlertPublisher, AlertRepository, AlertRuleRepository
from services.alert_auth.domain.rules import evaluate_reading
from shared.events import AlertEvent, IoTReadingEvent, parse_event

logger = structlog.get_logger()


class AlertHandler:
    """Orchestrator: handles an IoT reading event, evaluates alert rules, publishes any alerts.

    Depends only on domain ports — no framework imports.
    """

    def __init__(
        self,
        rule_repo: AlertRuleRepository,
        alert_repo: AlertRepository,
        publisher: AlertPublisher,
        cooldown_seconds: int = 60,
    ):
        self._rule_repo = rule_repo
        self._alert_repo = alert_repo
        self._publisher = publisher
        self._cooldown_seconds = cooldown_seconds

    async def __call__(self, body: bytes) -> None:
        event = parse_event(body)
        if not isinstance(event, IoTReadingEvent):
            return

        payload = event.payload
        alerts = await evaluate_reading(
            self._rule_repo, self._alert_repo,
            payload.device_id, payload.power_kw,
            self._cooldown_seconds,
        )

        for alert in alerts:
            alert_event = AlertEvent(
                alert_id=alert.id,
                device_id=alert.device_id,
                rule_id=alert.rule_id,
                message=alert.message,
                power_kw=alert.power_kw,
                threshold=alert.threshold,
                acknowledged=alert.acknowledged,
            )
            await self._publisher.publish_alert(alert_event.model_dump())
            logger.info("alert_published", alert_id=alert.id, device_id=alert.device_id)
