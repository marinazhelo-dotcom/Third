from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from services.telemetry.app.api import router
from services.telemetry.app.cache import build_cache
from services.telemetry.app.config import get_settings
from services.telemetry.app.consumer import Consumer
from services.telemetry.app.handler import EventHandler
from shared.logging import setup_logging
from shared.metrics import setup_metrics

setup_logging("telemetry")
logger = structlog.get_logger()


def _setup_tracing(app: FastAPI) -> None:
    resource = Resource.create({"service.name": "telemetry"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


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
_setup_tracing(app)
setup_metrics(app, "telemetry")
app.include_router(router)
