import asyncio
import logging
from collections.abc import Awaitable, Callable

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.circuit_breaker import CircuitBreaker
from app.config import AppConfig, SourceConfig
from app.db import SessionLocal
from app.models import DB_SOURCE_MODELS
from app.sources.base import SourceProvider
from app.sources.factory import get_source

logger = logging.getLogger(__name__)
# __name__ is the name of the module (app.poller)


class Poller:
    def __init__(self, config: AppConfig):
        self.config = config
        self._client = httpx.AsyncClient(timeout=10.0)
        self._breakers: dict[str, CircuitBreaker] = {}
        self._tasks: list[asyncio.Task] = []
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
                failure_threshold=config.breaker.failure_threshold,
                cooldown_seconds=config.breaker.cooldown_seconds,
                half_open_max_probes=config.breaker.half_open_max_probes,
            )

    def breaker_for(self, name: str) -> CircuitBreaker:
        return self._breakers[name]

    def breakers(self) -> dict[str, CircuitBreaker]:
        return self._breakers

    async def start(self) -> None:
        for source in self.config.sources:
            task = asyncio.create_task( # sends to the event loop
                # _run_source will be executed when the event loop next has a turn
                # (next "await" after this function returns)
                self._run_source(source), name=f"poll-{source.name}"
            )
            self._tasks.append(task)
        logger.info("Poller started with %d source(s)", len(self._tasks))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._client.aclose()
        logger.info("Poller stopped")

    async def _run_source(self, source: SourceConfig) -> None:
        provider = get_source(source, self._client)
        breaker = self._breakers[source.name]
        model_cls = DB_SOURCE_MODELS[source.type]
        logger.info("Poller %s started (every %.1fs)", source.name, source.interval_seconds)

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
        if not breaker.allow_request():
            logger.debug("Poller %s: circuit open, skipping", source.name)
            return
        try:
            readings = await self._retry(provider.fetch)()
            await self._persist(model_cls, readings)
            breaker.record_success()
            logger.info("Poller %s: stored %d reading(s)", source.name, len(readings))
        except Exception as exc:
            breaker.record_failure()
            logger.warning("Poller %s failed: %s", source.name, exc)

    async def _persist(self, model_cls: type, readings: list) -> None:
        async with SessionLocal() as session:
            for reading in readings:
                # model_dump() converts the Pydantic model to a dictionary
                # ** unpacks the dictionary into keyword arguments
                # model_cls(dict) creates a new db object
                session.add(model_cls(**reading.model_dump()))
            await session.commit()
