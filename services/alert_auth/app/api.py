from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.alert_auth.app.db import get_session
from services.alert_auth.app.models import Alert, AlertRule, User
from services.alert_auth.app.security import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)

router = APIRouter()

admin_only = require_roles(ROLE_ADMIN)
operator_or_admin = require_roles(ROLE_OPERATOR, ROLE_ADMIN)


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "viewer"


class RuleCreate(BaseModel):
    device_id: str
    threshold: float


@router.post("/auth/login")
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad credentials")
    token = create_access_token(user.id, user.role, user.username)
    return {"access_token": token, "username": user.username, "role": user.role}


@router.post("/auth/register")
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(admin_only),
) -> dict:
    """Create a new user (admin only)."""
    existing = await session.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(username=body.username, password_hash=hash_password(body.password), role=body.role)
    session.add(user)
    await session.commit()
    return {"id": user.id, "username": user.username, "role": user.role}


@router.get("/users")
async def list_users(
    session: AsyncSession = Depends(get_session), _: dict = Depends(admin_only)
) -> list[dict]:
    result = await session.execute(select(User))
    return [{"id": u.id, "username": u.username, "role": u.role} for u in result.scalars().all()]


@router.get("/rules")
async def list_rules(
    session: AsyncSession = Depends(get_session), _: dict = Depends(get_current_user)
) -> list[dict]:
    result = await session.execute(select(AlertRule))
    return [
        {"id": r.id, "device_id": r.device_id, "threshold": r.threshold, "enabled": r.enabled}
        for r in result.scalars().all()
    ]


@router.post("/rules")
async def create_rule(
    body: RuleCreate,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(admin_only),
) -> dict:
    rule = AlertRule(device_id=body.device_id, threshold=body.threshold)
    session.add(rule)
    await session.commit()
    return {"id": rule.id, "device_id": rule.device_id, "threshold": rule.threshold}


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(admin_only),
) -> dict:
    """Delete a rule; idempotent — deleting a missing rule is a no-op success."""
    rule = await session.get(AlertRule, rule_id)
    if rule is not None:
        await session.delete(rule)
        await session.commit()
    return {"deleted": rule_id}


@router.get("/alerts")
async def list_alerts(
    limit: int = Query(default=50, ge=1, le=500), 
    # specifying default makes it optional
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(get_current_user),
) -> list[dict]:
    result = await session.execute(
        select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    )
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
        for a in result.scalars().all()
    ]


@router.post("/alerts/{alert_id}/ack")
async def ack_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
    user: dict = Depends(operator_or_admin),
) -> dict:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    alert.acknowledged_by = user["username"]
    await session.commit()
    return {"id": alert.id, "acknowledged": True}
