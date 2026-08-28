from services.alert_auth.domain.models import AlertRule
from services.alert_auth.domain.ports import AlertRuleRepository


class ListRules:
    """Use case: list all alert rules."""

    def __init__(self, repo: AlertRuleRepository):
        self._repo = repo

    async def execute(self) -> list[dict]:
        rules = await self._repo.list_all()
        return [
            {"id": r.id, "device_id": r.device_id, "threshold": r.threshold, "enabled": r.enabled}
            for r in rules
        ]


class CreateRule:
    """Use case: create a new alert rule (admin)."""

    def __init__(self, repo: AlertRuleRepository):
        self._repo = repo

    async def execute(self, device_id: str, threshold: float) -> dict:
        rule = await self._repo.create(AlertRule(device_id=device_id, threshold=threshold))
        return {"id": rule.id, "device_id": rule.device_id, "threshold": rule.threshold}


class DeleteRule:
    """Use case: delete an alert rule (idempotent, admin)."""

    def __init__(self, repo: AlertRuleRepository):
        self._repo = repo

    async def execute(self, rule_id: int) -> None:
        await self._repo.delete(rule_id)
