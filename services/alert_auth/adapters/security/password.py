import bcrypt

from services.alert_auth.domain.ports import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    """Implements the PasswordHasher port using bcrypt."""

    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())
