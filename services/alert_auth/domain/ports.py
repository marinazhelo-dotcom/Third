from __future__ import annotations

from abc import ABC, abstractmethod

from services.alert_auth.domain.models import Alert, AlertRule, User


class UserRepository(ABC):
    """Port: persist and retrieve User aggregates."""

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def list_all(self) -> list[User]: ...


class AlertRuleRepository(ABC):
    """Port: persist and retrieve AlertRule aggregates."""

    @abstractmethod
    async def list_enabled_for_device(self, device_id: str) -> list[AlertRule]: ...

    @abstractmethod
    async def get(self, rule_id: int) -> AlertRule | None: ...

    @abstractmethod
    async def list_all(self) -> list[AlertRule]: ...

    @abstractmethod
    async def create(self, rule: AlertRule) -> AlertRule: ...

    @abstractmethod
    async def delete(self, rule_id: int) -> None: ...

    @abstractmethod
    async def touch_last_alert(self, rule_id: int) -> None: ...


class AlertRepository(ABC):
    """Port: persist and retrieve Alert records."""

    @abstractmethod
    async def create(self, alert: Alert) -> Alert: ...

    @abstractmethod
    async def list_recent(self, limit: int) -> list[Alert]: ...

    @abstractmethod
    async def ack(self, alert_id: int, username: str) -> Alert | None: ...


class AlertPublisher(ABC):
    """Port: publish alert events for real-time delivery (e.g. Redis pub/sub)."""

    @abstractmethod
    async def publish_alert(self, event: dict) -> None: ...


class PasswordHasher(ABC):
    """Port: hash and verify passwords."""

    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password: str, hashed: str) -> bool: ...


class TokenService(ABC):
    """Port: create and decode authentication tokens."""

    @abstractmethod
    def create_token(self, user_id: int, role: str, username: str) -> str: ...

    @abstractmethod
    def decode_token(self, token: str) -> dict: ...
