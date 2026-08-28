"""Shared Prometheus metrics + /metrics endpoint for all services.

Usage in a service's main.py:
    from shared.metrics import metrics_endpoint, http_metrics_middleware, setup_metrics
    setup_metrics(app, "ingest")

Or for custom counters:
    from shared.metrics import COUNTERS, GAUGES
    COUNTERS["iot_readings_total"].labels(device_id="solar-1").inc()
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

# ---------------------------------------------------------------------------
# Pre-defined metrics for all services
# ---------------------------------------------------------------------------

# HTTP metrics (per-service, labeled by method + status)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Ingest-specific
IOT_READINGS_TOTAL = Counter(
    "iot_readings_total",
    "Total IoT readings polled",
    ["device_id", "source"],
)
EVENTS_PUBLISHED_TOTAL = Counter(
    "events_published_total",
    "Total events published to RabbitMQ",
    ["routing_key"],
)
CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["source"],
)

# Telemetry-specific
TELEMETRY_EVENTS_CONSUMED_TOTAL = Counter(
    "telemetry_events_consumed_total",
    "Total events consumed from RabbitMQ",
)
TELEMETRY_READINGS_STORED_TOTAL = Counter(
    "telemetry_readings_stored_total",
    "Total readings persisted to PostgreSQL",
)

# Alert/Auth-specific
ALERTS_RAISED_TOTAL = Counter(
    "alerts_raised_total",
    "Total alerts created",
)
ALERTS_ACKNOWLEDGED_TOTAL = Counter(
    "alerts_acknowledged_total",
    "Total alerts acknowledged",
)


# ---------------------------------------------------------------------------
# FastAPI middleware + endpoint
# ---------------------------------------------------------------------------

_STATE_MAP = {0: "closed", 1: "half_open", 2: "open"}


async def metrics_middleware(request, call_next):
    """ASGI middleware that records request duration in HTTP_REQUEST_DURATION."""
    method = request.method
    path = request.url.path
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    HTTP_REQUEST_DURATION.labels(method=method, endpoint=path, status=response.status_code).observe(elapsed)
    return response


def metrics_endpoint(request=None):
    """Return the latest Prometheus metrics as plain text."""
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(generate_latest(REGISTRY), media_type="text/plain")


def setup_metrics(app: "FastAPI", service_name: str) -> None:
    """Wire metrics middleware and /metrics endpoint into a FastAPI app."""
    from shared.logging import get_logger

    logger = get_logger()
    app.middleware("http")(metrics_middleware)
    app.add_route("/metrics", metrics_endpoint, methods=["GET"])
    logger.info("Prometheus /metrics endpoint enabled", service=service_name)
