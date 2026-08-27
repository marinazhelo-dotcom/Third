import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.alert_auth.adapters.persistence.models import User
from services.alert_auth.adapters.security.password import BcryptPasswordHasher
from services.alert_auth.adapters.security.jwt import PyJWTTokenService
from services.alert_auth.infrastructure.database import Base
from services.alert_auth.main import app

_hasher = BcryptPasswordHasher()
_tokens = PyJWTTokenService()


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


@pytest.fixture
async def client(session_factory):
    from services.alert_auth.adapters.security.fastapi_deps import set_token_service

    set_token_service(_tokens)
    app.state.hasher = _hasher
    app.state.tokens = _tokens
    app.state.session_factory = session_factory

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _seed_users(session_factory):
    async with session_factory() as session:
        session.add(User(username="admin", password_hash=_hasher.hash("admin123"), role="admin"))
        session.add(User(username="viewer", password_hash=_hasher.hash("viewer"), role="viewer"))
        await session.commit()


async def test_login_returns_token(client, session_factory):
    await _seed_users(session_factory)
    resp = await client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"
    assert data["access_token"]


async def test_login_bad_credentials(client, session_factory):
    await _seed_users(session_factory)
    resp = await client.post("/auth/login", json={"username": "admin", "password": "nope"})
    assert resp.status_code == 401


async def test_rules_requires_auth(client):
    resp = await client.get("/rules")
    assert resp.status_code == 401


async def test_viewer_cannot_create_rule(client, session_factory):
    await _seed_users(session_factory)
    token = _tokens.create_token(2, "viewer", "viewer")
    resp = await client.post(
        "/rules",
        json={"device_id": "solar-1", "threshold": 10.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_admin_can_create_rule(client, session_factory):
    await _seed_users(session_factory)
    token = _tokens.create_token(1, "admin", "admin")
    resp = await client.post(
        "/rules",
        json={"device_id": "solar-1", "threshold": 10.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["device_id"] == "solar-1"


async def test_delete_rule_is_idempotent(client, session_factory):
    """Deleting the same rule twice (or a missing rule) returns success both times."""
    await _seed_users(session_factory)
    token = _tokens.create_token(1, "admin", "admin")

    create = await client.post(
        "/rules",
        json={"device_id": "solar-1", "threshold": 10.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    rule_id = create.json()["id"]

    first = await client.delete(f"/rules/{rule_id}", headers={"Authorization": f"Bearer {token}"})
    assert first.status_code == 200
    assert first.json() == {"deleted": rule_id}

    second = await client.delete(f"/rules/{rule_id}", headers={"Authorization": f"Bearer {token}"})
    assert second.status_code == 200
    assert second.json() == {"deleted": rule_id}

    missing = await client.delete("/rules/9999", headers={"Authorization": f"Bearer {token}"})
    assert missing.status_code == 200
    assert missing.json() == {"deleted": 9999}
