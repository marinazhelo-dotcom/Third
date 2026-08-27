import asyncio
from collections.abc import Awaitable, Callable

import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from app.circuit_breaker import CircuitBreaker
from app.config import AppConfig, SourceConfig
from app.db import SessionLocal
from app.models import DB_SOURCE_MODELS
from app.publisher import Publisher
from app.sources.base import SourceProvider
from app.sources.factory import get_source
from shared.events import ROUTING_KEYS, make_reading_event
from shared.metrics import IOT_READINGS_TOTAL

logger = structlog.get_logger()


class Poller:
    """Runs one background polling loop per configured source.

    Each loop fetches from its source, persists readings to the database,
    and publishes them to RabbitMQ — guarded by a per-source circuit breaker.
    """

    def __init__(self, config: AppConfig, rabbitmq_url: str | None = None):
        """Set up the HTTP client, per-source circuit breakers, retry policy, and publisher."""
        self.config = config
        self._client = httpx.AsyncClient(timeout=10.0)
        self._breakers: dict[str, CircuitBreaker] = {}
        self._tasks: list[asyncio.Task] = []
        self._publisher = Publisher(rabbitmq_url) if rabbitmq_url else None
        # retry is a decorator that will retry the function if it fails
        # _retry is a callable that takes a function and returns another callable,
        # which when awaited returns a list.
        self._retry: Callable[..., Callable[..., Awaitable[list]]] = retry(
            stop=stop_after_attempt(config.retry.max_attempts),
            wait=wait_exponential(multiplier=config.retry.base_delay_seconds, max=10),
            reraise=True,
        )

        for source in config.sources:
            self._breakers[source.name] = CircuitBreaker(
                source_name=source.name,
                failure_threshold=config.breaker.failure_threshold,
                cooldown_seconds=config.breaker.cooldown_seconds,
                half_open_max_probes=config.breaker.half_open_max_probes,
            )

    def breaker_for(self, name: str) -> CircuitBreaker:
        """Return the circuit breaker for the named source (e.g. "iot")."""
        return self._breakers[name]

    def breakers(self) -> dict[str, CircuitBreaker]:
        """Return a mapping of source name -> circuit breaker (used by /status)."""
        return self._breakers

    async def start(self) -> None:
        """Connect to RabbitMQ (best-effort) and spawn one async task per source."""
        if self._publisher is not None:
            try:
                await self._publisher.connect()
                logger.info("rabbitmq_connected")
            except Exception as exc:
                logger.warning("rabbitmq_connect_failed", error=str(exc))
        for source in self.config.sources:
            task = asyncio.create_task( # sends to the event loop
                # _run_source will be executed when the event loop next has a turn
                # (next "await" after this function returns)
                self._run_source(source), name=f"poll-{source.name}"
            )
            self._tasks.append(task)
        logger.info("poller_started", source_count=len(self._tasks))

    async def stop(self) -> None:
        """Cancel all polling tasks and close the HTTP client and RabbitMQ connection."""
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._client.aclose()
        if self._publisher is not None:
            await self._publisher.close()
        logger.info("poller_stopped")

    async def _run_source(self, source: SourceConfig) -> None:
        """Run the polling loop for a single source until cancelled.

        Fetches, then sleeps for the source's configured interval, forever.
        """
        provider = get_source(source, self._client)
        breaker = self._breakers[source.name]
        model_cls = DB_SOURCE_MODELS[source.type]
        logger.info("source_started", source=source.name, interval=source.interval_seconds)

        while True:
            await self._poll_once(source, provider, breaker, model_cls)
            await asyncio.sleep(source.interval_seconds)

    async def _poll_once(
        self,
        source: SourceConfig,
        provider: SourceProvider,
        breaker: CircuitBreaker,
        model_cls: type, # name of the model class
    ) -> None:
        """Perform one poll cycle: fetch (with retry), persist, then publish.

        Updates the circuit breaker with success/failure. Publishing only
        happens after a successful persist, and its own failures are logged
        (not counted against the source).
        """
        if not breaker.allow_request():
            logger.debug("circuit_open_skip", source=source.name)
            return
        try:
            readings = await self._retry(provider.fetch)()
            await self._persist(model_cls, readings)
            breaker.record_success()
            for r in readings:
                IOT_READINGS_TOTAL.labels(device_id=getattr(r, "device_id", "unknown"), source=source.name).inc()
            logger.info("readings_stored", source=source.name, count=len(readings))
        except Exception as exc:
            breaker.record_failure()
            logger.warning("poll_failed", source=source.name, error=str(exc))
            return
        await self._publish_readings(source.type, readings)

    async def _publish_readings(self, source_type: str, readings: list[BaseModel]) -> None:
        """Publish each reading as an event to RabbitMQ (best-effort).

        Failures here are logged but do not affect the source's circuit breaker.
        """
        if self._publisher is None or not readings:
            return
        routing_key = ROUTING_KEYS.get(source_type, f"{source_type}.reading")
        for reading in readings:
            event = make_reading_event(source_type, reading.model_dump(exclude_none=True))
            try:
                await self._publisher.publish(event, routing_key)
            except Exception as exc:
                logger.warning("publish_failed", source_type=source_type, error=str(exc))

    async def _persist(self, model_cls: type, readings: list[BaseModel]) -> None:
        """Insert the fetched readings into the database in one transaction."""
        async with SessionLocal() as session:
            for reading in readings:
                # model_dump() converts the Pydantic model to a dictionary
                # ** unpacks the dictionary into keyword arguments
                # model_cls(dict) creates a new db object
                session.add(model_cls(**reading.model_dump()))
            await session.commit()
