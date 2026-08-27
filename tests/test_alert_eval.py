import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.alert_auth.adapters.persistence.models import AlertRule
from services.alert_auth.adapters.persistence.repository import SqlAlertRepository, SqlAlertRuleRepository
from services.alert_auth.domain.rules import evaluate_reading
from services.alert_auth.infrastructure.database import Base


@pytest.fixture
async def engine(tmp_path):
    db_path = tmp_path / "alertauth.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


async def _add_rule(session_factory, device_id="solar-1", threshold=10.0):
    async with session_factory() as session:
        session.add(AlertRule(device_id=device_id, threshold=threshold))
        await session.commit()


async def test_breach_creates_alert(session_factory):
    await _add_rule(session_factory)
    async with session_factory() as session:
        rule_repo = SqlAlertRuleRepository(session)
        alert_repo = SqlAlertRepository(session)
        alerts = await evaluate_reading(rule_repo, alert_repo, "solar-1", 15.0)
    assert len(alerts) == 1
    assert alerts[0].device_id == "solar-1"
    assert alerts[0].power_kw == 15.0


async def test_no_breach_no_alert(session_factory):
    await _add_rule(session_factory)
    async with session_factory() as session:
        rule_repo = SqlAlertRuleRepository(session)
        alert_repo = SqlAlertRepository(session)
        alerts = await evaluate_reading(rule_repo, alert_repo, "solar-1", 5.0)
    assert alerts == []


async def test_cooldown_suppresses_repeat_alert(session_factory):
    await _add_rule(session_factory)
    async with session_factory() as session:
        rule_repo = SqlAlertRuleRepository(session)
        alert_repo = SqlAlertRepository(session)
        first = await evaluate_reading(rule_repo, alert_repo, "solar-1", 15.0)
    async with session_factory() as session:
        rule_repo = SqlAlertRuleRepository(session)
        alert_repo = SqlAlertRepository(session)
        second = await evaluate_reading(rule_repo, alert_repo, "solar-1", 20.0)
    assert len(first) == 1
    assert second == []


async def test_rule_for_other_device_ignored(session_factory):
    await _add_rule(session_factory, device_id="solar-1")
    async with session_factory() as session:
        rule_repo = SqlAlertRuleRepository(session)
        alert_repo = SqlAlertRepository(session)
        alerts = await evaluate_reading(rule_repo, alert_repo, "wind-3", 15.0)
    assert alerts == []
