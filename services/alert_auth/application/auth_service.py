from fastapi import HTTPException

from services.alert_auth.domain.ports import PasswordHasher, TokenService, UserRepository


class AuthLogin:
    """Use case: authenticate a user and return a JWT."""

    def __init__(self, user_repo: UserRepository, hasher: PasswordHasher, tokens: TokenService):
        self._users = user_repo
        self._hasher = hasher
        self._tokens = tokens

    async def execute(self, username: str, password: str) -> dict:
        user = await self._users.get_by_username(username)
        if user is None or not self._hasher.verify(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Bad credentials")
        token = self._tokens.create_token(user.id, user.role, user.username)
        return {"access_token": token, "username": user.username, "role": user.role}


class AuthRegister:
    """Use case: create a new user (admin only)."""

    def __init__(self, user_repo: UserRepository, hasher: PasswordHasher):
        self._users = user_repo
        self._hasher = hasher

    async def execute(self, username: str, password: str, role: str = "viewer") -> dict:
        existing = await self._users.get_by_username(username)
        if existing is not None:
            raise HTTPException(status_code=409, detail="Username already exists")
        from services.alert_auth.domain.models import User

        user = await self._users.create(
            User(username=username, password_hash=self._hasher.hash(password), role=role)
        )
        return {"id": user.id, "username": user.username, "role": user.role}
