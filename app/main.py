from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health_router, readings_router, status_router
from app.config import load_app_config
from app.poller import Poller


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_app_config()
    poller = Poller(config)
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
