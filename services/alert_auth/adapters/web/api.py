from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

import jwt as pyjwt

from services.alert_auth.adapters.persistence.repository import (
    SqlAlertRepository,
    SqlAlertRuleRepository,
    SqlUserRepository,
)
from services.alert_auth.adapters.security.fastapi_deps import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    _get_ts,
    get_current_user,
    require_roles,
)
from services.alert_auth.adapters.web.schemas import LoginRequest, RegisterRequest, RuleCreate
from services.alert_auth.application.alerts_service import AckAlert, ListAlerts
from services.alert_auth.application.auth_service import AuthLogin, AuthRegister
from services.alert_auth.application.rules_service import CreateRule, DeleteRule, ListRules

router = APIRouter()

admin_only = require_roles(ROLE_ADMIN)
operator_or_admin = require_roles(ROLE_OPERATOR, ROLE_ADMIN)


def _get_session_factory(request: Request):
    return request.app.state.session_factory


@router.post("/auth/login")
async def login(body: LoginRequest, request: Request) -> dict:
    sf = _get_session_factory(request)
    async with sf() as session:
        service = AuthLogin(SqlUserRepository(session), request.app.state.hasher, request.app.state.tokens)
        return await service.execute(body.username, body.password)


@router.get("/auth/verify")
async def verify_token(request: Request) -> JSONResponse:
    """Verify JWT token — used by nginx auth_request for proxy authentication.

    Accepts both ``Authorization: Bearer <token>`` and raw ``Authorization: <token>``
    (the latter is what nginx sends when forwarding the ``third_token`` cookie).
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:]
    else:
        token = auth
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    try:
        _get_ts().decode_token(token)
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
    return JSONResponse(content={"valid": True})


@router.post("/auth/register")
async def register(body: RegisterRequest, request: Request, _: dict = Depends(admin_only)) -> dict:
    sf = _get_session_factory(request)
    async with sf() as session:
        service = AuthRegister(SqlUserRepository(session), request.app.state.hasher)
        return await service.execute(body.username, body.password, body.role)


@router.get("/users")
async def list_users(request: Request, _: dict = Depends(admin_only)) -> list[dict]:
    sf = _get_session_factory(request)
    async with sf() as session:
        users = await SqlUserRepository(session).list_all()
        return [{"id": u.id, "username": u.username, "role": u.role} for u in users]


@router.get("/rules")
async def list_rules(request: Request, _: dict = Depends(get_current_user)) -> list[dict]:
    sf = _get_session_factory(request)
    async with sf() as session:
        return await ListRules(SqlAlertRuleRepository(session)).execute()


@router.post("/rules")
async def create_rule(body: RuleCreate, request: Request, _: dict = Depends(admin_only)) -> dict:
    sf = _get_session_factory(request)
    async with sf() as session:
        return await CreateRule(SqlAlertRuleRepository(session)).execute(body.device_id, body.threshold)


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, request: Request, _: dict = Depends(admin_only)) -> dict:
    """Delete a rule; idempotent — deleting a missing rule is a no-op success."""
    sf = _get_session_factory(request)
    async with sf() as session:
        await DeleteRule(SqlAlertRuleRepository(session)).execute(rule_id)
    return {"deleted": rule_id}


@router.get("/alerts")
async def list_alerts(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    # specifying default makes it optional
    _: dict = Depends(get_current_user),
) -> list[dict]:
    sf = _get_session_factory(request)
    async with sf() as session:
        return await ListAlerts(SqlAlertRepository(session)).execute(limit)


@router.post("/alerts/{alert_id}/ack")
async def ack_alert(alert_id: int, request: Request, user: dict = Depends(operator_or_admin)) -> dict:
    sf = _get_session_factory(request)
    async with sf() as session:
        return await AckAlert(SqlAlertRepository(session)).execute(alert_id, user["username"])
