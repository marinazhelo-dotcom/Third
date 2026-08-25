import asyncio
import logging
from collections.abc import Awaitable, Callable

import aio_pika

from shared.events import EXCHANGE, QUEUE_TELEMETRY_IOT

logger = logging.getLogger(__name__)

EventCallback = Callable[[bytes], Awaitable[None]]


class Consumer:
    """Consumes telemetry IoT events from RabbitMQ and hands each message body to a callback."""

    def __init__(self, url: str, on_event: EventCallback):
        self._url = url
        self._on_event = on_event
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None
        self._queue: aio_pika.RobustQueue | None = None
        self._task: asyncio.Task | None = None

    async def connect(self) -> None:
        """Connect, declare the exchange + durable queue, and bind it to the routing key."""
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)
        # QoS = Quality of Service (AMQP setting for how messages are delivered to a consumer)
        exchange = await self._channel.declare_exchange(
            EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
        )
        queue = await self._channel.declare_queue(QUEUE_TELEMETRY_IOT, durable=True)
        await queue.bind(exchange, routing_key="telemetry.iot")
        self._queue = queue

    async def start(self) -> None:
        """Connect and start the consume loop as a background task."""
        await self.connect()
        self._task = asyncio.create_task(self._consume(), name="telemetry-consumer")
        logger.info("Telemetry consumer started")

    async def _consume(self) -> None:
        """Loop forever, delivering each message body to the callback and acking it."""
        assert self._queue is not None
        # note: with python -O (optimize) assert is ignored
        async with self._queue.iterator() as iterator:
            async for message in iterator:
                async with message.process():
                    await self._on_event(message.body)

    async def stop(self) -> None:
        """Cancel the consume loop and close the RabbitMQ connection."""
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            # return_exceptions=True -> gather will RETURN all exceptions (to no one here)
            # return_exceptions=False -> gather will RAISE an exception if any task raises an exception
        if self._connection is not None:
            await self._connection.close()
        logger.info("Telemetry consumer stopped")
