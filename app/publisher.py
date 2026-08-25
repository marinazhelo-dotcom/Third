import aio_pika

from shared.events import EXCHANGE, ReadingEvent


class Publisher:
    """Publishes reading events to RabbitMQ.

    Wraps a robust connection + channel and a single topic exchange; each
    event is sent with a routing key so consumers can bind selectively.
    """

    def __init__(self, url: str):
        self._url = url
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None
        self._exchange: aio_pika.RobustExchange | None = None

    async def connect(self) -> None:
        """Connect to RabbitMQ and declare the durable topic exchange."""
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
        )

    async def publish(self, event: ReadingEvent, routing_key: str) -> None:
        """Serialize the event to JSON and publish it with the given routing key."""
        if self._exchange is None:
            raise RuntimeError("Publisher is not connected")
        message = aio_pika.Message(
            event.model_dump_json().encode(), # == encode("utf-8") -> bytes
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        # bytes vs str
        # a = "é"  -> one character, U+00E9
        # b = a.encode("utf-8")  -> b'\xc3\xa9' -> two bytes: 195, 169
        await self._exchange.publish(message, routing_key=routing_key)

    async def close(self) -> None:
        """Close the RabbitMQ connection."""
        if self._connection is not None:
            await self._connection.close()
