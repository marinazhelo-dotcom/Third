from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.alert_auth.adapters.persistence.models import Alert as AlertORM
from services.alert_auth.adapters.persistence.models import AlertRule as AlertRuleORM
from services.alert_auth.adapters.persistence.models import User as UserORM
from services.alert_auth.domain.models import Alert, AlertRule, User
from services.alert_auth.domain.ports import AlertRepository, AlertRuleRepository, UserRepository


# ---------------------------------------------------------------------------
# Mapping helpers: ORM <-> domain dataclasses
# ---------------------------------------------------------------------------

def _user_to_domain(orm: UserORM) -> User:
    return User(id=orm.id, username=orm.username, password_hash=orm.password_hash, role=orm.role)


def _rule_to_domain(orm: AlertRuleORM) -> AlertRule:
    return AlertRule(
        id=orm.id, device_id=orm.device_id, threshold=orm.threshold,
        enabled=orm.enabled, last_alert_at=orm.last_alert_at,
    )


def _alert_to_domain(orm: AlertORM) -> Alert:
    return Alert(
        id=orm.id, device_id=orm.device_id, rule_id=orm.rule_id,
        message=orm.message, power_kw=orm.power_kw, threshold=orm.threshold,
        created_at=orm.created_at, acknowledged=orm.acknowledged,
        acknowledged_by=orm.acknowledged_by,
    )


# ---------------------------------------------------------------------------
# UserRepository (SQLAlchemy adapter)
# ---------------------------------------------------------------------------

class SqlUserRepository(UserRepository):
    """Implements the UserRepository port using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self._s = session

    async def get_by_username(self, username: str) -> User | None:
        result = await self._s.execute(select(UserORM).where(UserORM.username == username))
        orm = result.scalar_one_or_none()
        return _user_to_domain(orm) if orm else None

    async def create(self, user: User) -> User:
        orm = UserORM(username=user.username, password_hash=user.password_hash, role=user.role)
        self._s.add(orm)
        await self._s.commit()
        await self._s.refresh(orm)
        return _user_to_domain(orm)

    async def list_all(self) -> list[User]:
        result = await self._s.execute(select(UserORM))
        return [_user_to_domain(u) for u in result.scalars().all()]


# ---------------------------------------------------------------------------
# AlertRuleRepository (SQLAlchemy adapter)
# ---------------------------------------------------------------------------

class SqlAlertRuleRepository(AlertRuleRepository):
    """Implements the AlertRuleRepository port using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self._s = session

    async def list_enabled_for_device(self, device_id: str) -> list[AlertRule]:
        result = await self._s.execute(
            select(AlertRuleORM).where(
                AlertRuleORM.device_id == device_id, AlertRuleORM.enabled.is_(True)
            )
        )
        return [_rule_to_domain(r) for r in result.scalars().all()]

    async def get(self, rule_id: int) -> AlertRule | None:
        orm = await self._s.get(AlertRuleORM, rule_id)
        return _rule_to_domain(orm) if orm else None

    async def list_all(self) -> list[AlertRule]:
        result = await self._s.execute(select(AlertRuleORM))
        return [_rule_to_domain(r) for r in result.scalars().all()]

    async def create(self, rule: AlertRule) -> AlertRule:
        orm = AlertRuleORM(device_id=rule.device_id, threshold=rule.threshold, enabled=rule.enabled)
        self._s.add(orm)
        await self._s.commit()
        await self._s.refresh(orm)
        return _rule_to_domain(orm)

    async def delete(self, rule_id: int) -> None:
        orm = await self._s.get(AlertRuleORM, rule_id)
        if orm is not None:
            await self._s.delete(orm)
            await self._s.commit()

    async def touch_last_alert(self, rule_id: int) -> None:
        from datetime import datetime, timezone

        orm = await self._s.get(AlertRuleORM, rule_id)
        if orm is not None:
            orm.last_alert_at = datetime.now(timezone.utc)
            await self._s.commit()


# ---------------------------------------------------------------------------
# AlertRepository (SQLAlchemy adapter)
# ---------------------------------------------------------------------------

class SqlAlertRepository(AlertRepository):
    """Implements the AlertRepository port using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self._s = session

    async def create(self, alert: Alert) -> Alert:
        orm = AlertORM(
            device_id=alert.device_id, rule_id=alert.rule_id,
            message=alert.message, power_kw=alert.power_kw, threshold=alert.threshold,
        )
        self._s.add(orm)
        await self._s.commit()
        await self._s.refresh(orm)
        return _alert_to_domain(orm)

    async def list_recent(self, limit: int) -> list[Alert]:
        result = await self._s.execute(
            select(AlertORM).order_by(AlertORM.created_at.desc()).limit(limit)
        )
        return [_alert_to_domain(a) for a in result.scalars().all()]

    async def ack(self, alert_id: int, username: str) -> Alert | None:
        orm = await self._s.get(AlertORM, alert_id)
        if orm is None:
            return None
        orm.acknowledged = True
        orm.acknowledged_by = username
        await self._s.commit()
        return _alert_to_domain(orm)
