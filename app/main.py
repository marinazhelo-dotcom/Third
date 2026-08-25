import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health_router, readings_router, status_router
from app.config import get_settings, load_app_config
from app.poller import Poller

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_app_config()
    poller = Poller(config, rabbitmq_url=get_settings().rabbitmq_url)
    app.state.poller = poller
    await poller.start()
    try:
        yield
    finally:
        await poller.stop()


app = FastAPI(title="Third Ingest Engine", lifespan=lifespan)

app.include_router(health_router)
app.include_router(readings_router)
app.include_router(status_router)
