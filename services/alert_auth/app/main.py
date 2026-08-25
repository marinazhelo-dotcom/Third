import asyncio
import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from sqlalchemy import select

from services.alert_auth.app.api import router as api_router
from services.alert_auth.app.config import get_settings
from services.alert_auth.app.consumer import Consumer
from services.alert_auth.app.db import SessionLocal
from services.alert_auth.app.handler import AlertHandler
from services.alert_auth.app.models import User
from services.alert_auth.app.security import ROLE_ADMIN, hash_password
from services.alert_auth.app.ws import redis_subscriber, router as ws_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_admin() -> None:
    """Create the initial admin user if none exists (admin / admin123)."""
    async with SessionLocal() as session:
        existing = await session.execute(select(User).where(User.username == "admin"))
        if existing.scalar_one_or_none() is None:
            session.add(
                User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    role=ROLE_ADMIN,
                )
            )
            await session.commit()
            logger.info("Seeded admin user (admin / admin123)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await seed_admin()

    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    consumer = Consumer(settings.rabbitmq_url, on_event=AlertHandler(redis_client))
    await consumer.start()
    subscriber_task = asyncio.create_task(redis_subscriber(settings.redis_url))

    try:
        yield
    finally:
        await consumer.stop()
        subscriber_task.cancel()
        await asyncio.gather(subscriber_task, return_exceptions=True)
        await redis_client.aclose()


app = FastAPI(title="Alert/Auth Service", lifespan=lifespan)
app.include_router(api_router)
app.include_router(ws_router)
