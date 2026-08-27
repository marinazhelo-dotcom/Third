import asyncio
import logging
from collections.abc import Awaitable, Callable

import aio_pika

logger = logging.getLogger(__name__)

EventCallback = Callable[[bytes], Awaitable[None]]


class RabbitMQConsumer:
    """Connects to RabbitMQ, declares an exchange + durable queue, and delivers messages to a callback.

    Subclass for extra logic (e.g. telemetry's publish-to-redis), or use directly with a callback.
    """

    def __init__(self, url: str, queue_name: str, on_event: EventCallback, *, routing_key: str = "telemetry.iot", task_name: str = "consumer", prefetch: int = 10):
        self._url = url
        self._queue_name = queue_name
        self._routing_key = routing_key
        self._task_name = task_name
        self._prefetch = prefetch
        self._on_event = on_event
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None
        self._queue: aio_pika.RobustQueue | None = None
        self._task: asyncio.Task | None = None

    async def connect(self) -> None:
        """Connect to RabbitMQ, declare the exchange + queue, and bind them."""
        from shared.events import EVENTS_EXCHANGE

        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self._prefetch)
        exchange = await self._channel.declare_exchange(
            EVENTS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True,
        )
        queue = await self._channel.declare_queue(self._queue_name, durable=True)
        await queue.bind(exchange, routing_key=self._routing_key)
        self._queue = queue

    async def start(self) -> None:
        """Connect and begin consuming in a background task."""
        await self.connect()
        self._task = asyncio.create_task(self._consume(), name=self._task_name)
        logger.info("%s started", self._task_name)

    async def _consume(self) -> None:
        """Loop forever, passing each message body to the callback and acking on success."""
        assert self._queue is not None
        async with self._queue.iterator() as iterator:
            async for message in iterator:
                async with message.process():
                    await self._on_event(message.body)

    async def stop(self) -> None:
        """Cancel the consume loop and close the RabbitMQ connection."""
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        if self._connection is not None:
            await self._connection.close()
        logger.info("%s stopped", self._task_name)
