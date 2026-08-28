from fastapi import HTTPException

from services.alert_auth.domain.ports import AlertRepository


class ListAlerts:
    """Use case: list recent alerts (any authenticated user)."""

    def __init__(self, repo: AlertRepository):
        self._repo = repo

    async def execute(self, limit: int = 50) -> list[dict]:
        alerts = await self._repo.list_recent(limit)
        return [
            {
                "id": a.id,
                "device_id": a.device_id,
                "message": a.message,
                "power_kw": a.power_kw,
                "threshold": a.threshold,
                "created_at": a.created_at,
                "acknowledged": a.acknowledged,
                "acknowledged_by": a.acknowledged_by,
            }
            for a in alerts
        ]


class AckAlert:
    """Use case: acknowledge an alert (operator or admin)."""

    def __init__(self, repo: AlertRepository):
        self._repo = repo

    async def execute(self, alert_id: int, username: str) -> dict:
        alert = await self._repo.ack(alert_id, username)
        if alert is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"id": alert.id, "acknowledged": True}
