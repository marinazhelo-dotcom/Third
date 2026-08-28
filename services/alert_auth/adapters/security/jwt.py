from datetime import datetime, timedelta, timezone

import jwt

from services.alert_auth.domain.ports import TokenService
from services.alert_auth.infrastructure.config import get_settings


class PyJWTTokenService(TokenService):
    """Implements the TokenService port using PyJWT."""

    def create_token(self, user_id: int, role: str, username: str) -> str:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "role": role,
            "username": username,
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def decode_token(self, token: str) -> dict:
        settings = get_settings()
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
