from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api import health_router, readings_router, status_router
from app.config import get_settings, load_app_config
from app.poller import Poller
from shared.logging import setup_logging
from shared.metrics import setup_metrics

setup_logging("ingest")


def _setup_tracing(app: FastAPI) -> None:
    resource = Resource.create({"service.name": "ingest"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


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
_setup_tracing(app)
setup_metrics(app, "ingest")

app.include_router(health_router)
app.include_router(readings_router)
app.include_router(status_router)
