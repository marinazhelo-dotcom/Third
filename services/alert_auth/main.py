import asyncio
import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from sqlalchemy import select

from services.alert_auth.adapters.messaging.rabbitmq_consumer import Consumer
from services.alert_auth.adapters.messaging.redis_publisher import RedisAlertPublisher
from services.alert_auth.adapters.persistence.models import User as UserORM
from services.alert_auth.adapters.persistence.repository import (
    SqlAlertRepository,
    SqlAlertRuleRepository,
    SqlUserRepository,
)
from services.alert_auth.adapters.security.fastapi_deps import set_token_service
from services.alert_auth.adapters.security.jwt import PyJWTTokenService
from services.alert_auth.adapters.security.password import BcryptPasswordHasher
from services.alert_auth.adapters.web.api import router as api_router
from services.alert_auth.adapters.web.ws import redis_subscriber, router as ws_router
from services.alert_auth.application.event_handler import AlertHandler
from services.alert_auth.infrastructure.config import get_settings
from services.alert_auth.infrastructure.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_admin(session_factory) -> None:
    """Create the initial admin user if none exists (admin / admin123)."""
    async with session_factory() as session:
        existing = await session.execute(select(UserORM).where(UserORM.username == "admin"))
        if existing.scalar_one_or_none() is None:
            hasher = BcryptPasswordHasher()
            session.add(
                UserORM(
                    username="admin",
                    password_hash=hasher.hash("admin123"),
                    role="admin",
                )
            )
            await session.commit()
            logger.info("Seeded admin user (admin / admin123)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # --- Infrastructure singletons ---
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    tokens = PyJWTTokenService()
    hasher = BcryptPasswordHasher()
    publisher = RedisAlertPublisher(redis_client)

    # Wire FastAPI security Depends to the JWT implementation
    set_token_service(tokens)

    # Store on app.state so endpoints + tests can access them
    app.state.hasher = hasher
    app.state.tokens = tokens
    app.state.session_factory = SessionLocal

    # --- Background handler (needs its own session + repos) ---
    handler_session = SessionLocal()
    handler = AlertHandler(
        rule_repo=SqlAlertRuleRepository(handler_session),
        alert_repo=SqlAlertRepository(handler_session),
        publisher=publisher,
        cooldown_seconds=settings.alert_cooldown_seconds,
    )

    # --- Seed admin ---
    await seed_admin(SessionLocal)

    # --- Start background tasks ---
    consumer = Consumer(settings.rabbitmq_url, on_event=handler)
    await consumer.start()
    subscriber_task = asyncio.create_task(redis_subscriber(settings.redis_url))

    try:
        yield
    finally:
        await consumer.stop()
        subscriber_task.cancel()
        await asyncio.gather(subscriber_task, return_exceptions=True)
        await handler_session.dispose()
        await redis_client.aclose()


app = FastAPI(title="Alert/Auth Service", lifespan=lifespan)
app.include_router(api_router)
app.include_router(ws_router)
