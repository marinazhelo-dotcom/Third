from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ALERTAUTH_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://telemetry:telemetry@localhost:5432/alertauth"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-only-secret-key-change-me-in-production-0001"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    alert_cooldown_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
