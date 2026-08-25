import asyncio
import logging
from collections.abc import Awaitable, Callable

import aio_pika

from shared.events import EVENTS_EXCHANGE

logger = logging.getLogger(__name__)

# RabbitMQ queue this service consumes IoT events from (to evaluate alert rules).
ALERTAUTH_IOT_QUEUE = "alertauth.iot.readings"

EventCallback = Callable[[bytes], Awaitable[None]]


class Consumer:
    """Consumes IoT events from RabbitMQ and hands each message body to a callback."""

    def __init__(self, url: str, on_event: EventCallback):
        self._url = url
        self._on_event = on_event
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None
        self._queue: aio_pika.RobustQueue | None = None
        self._task: asyncio.Task | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)
        exchange = await self._channel.declare_exchange(
            EVENTS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
        )
        queue = await self._channel.declare_queue(ALERTAUTH_IOT_QUEUE, durable=True)
        await queue.bind(exchange, routing_key="telemetry.iot")
        self._queue = queue

    async def start(self) -> None:
        await self.connect()
        self._task = asyncio.create_task(self._consume(), name="alertauth-consumer")
        logger.info("Alert/Auth consumer started")

    async def _consume(self) -> None:
        assert self._queue is not None
        async with self._queue.iterator() as iterator:
            async for message in iterator:
                async with message.process():
                    await self._on_event(message.body)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        if self._connection is not None:
            await self._connection.close()
        logger.info("Alert/Auth consumer stopped")
