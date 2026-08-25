import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.telemetry.app.api import router
from services.telemetry.app.cache import build_cache
from services.telemetry.app.config import get_settings
from services.telemetry.app.consumer import Consumer
from services.telemetry.app.handler import EventHandler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the Redis cache and RabbitMQ consumer for the app's lifetime, clean up on shutdown."""
    cache = build_cache()
    app.state.cache = cache
    consumer = Consumer(get_settings().rabbitmq_url, on_event=EventHandler(cache))
    await consumer.start()
    try:
        yield
    finally:
        await consumer.stop()
        await cache.close()


app = FastAPI(title="Telemetry Service", lifespan=lifespan)
app.include_router(router)
