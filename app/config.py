from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BreakerConfig(BaseModel):
    failure_threshold: int = Field(default=5, gt=0)
    cooldown_seconds: float = Field(default=30.0, gt=0)
    half_open_max_probes: int = Field(default=3, gt=0)


class RetryConfig(BaseModel):
    max_attempts: int = Field(default=3, gt=0)
    base_delay_seconds: float = Field(default=1.0, gt=0)


class SourceConfig(BaseModel):
    name: str
    type: str
    url: str
    interval_seconds: float = Field(gt=0)
    mock: bool = True


class AppConfig(BaseModel):
    breaker: BreakerConfig = Field(default_factory=BreakerConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    sources: list[SourceConfig] = Field(default_factory=list)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="THIRD_", env_file=".env", extra="ignore")

    config_path: Path = Path("config.yaml")
    database_url: str = "sqlite+aiosqlite:///./third.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_app_config() -> AppConfig:
    settings = get_settings()
    if settings.config_path.exists():
        raw = yaml.safe_load(settings.config_path.read_text()) or {}
        return AppConfig(**raw)
    return AppConfig()
