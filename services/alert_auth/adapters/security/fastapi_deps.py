import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.alert_auth.domain.ports import TokenService

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"

_bearer = HTTPBearer(auto_error=False)

# TokenService instance — set by composition root before routes are used.
_token_service: TokenService | None = None


def set_token_service(ts: TokenService) -> None:
    """Bind the TokenService implementation for FastAPI Depends to use."""
    global _token_service
    _token_service = ts


def _get_ts() -> TokenService:
    assert _token_service is not None, "TokenService not wired — call set_token_service() first"
    return _token_service


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    try:
        return _get_ts().decode_token(credentials.credentials)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except pyjwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def require_roles(*allowed: str):
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return user

    return dependency
