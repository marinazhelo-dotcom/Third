import aio_pika

from shared.events import EXCHANGE, ReadingEvent


class Publisher:
    def __init__(self, url: str):
        self._url = url
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None
        self._exchange: aio_pika.RobustExchange | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
        )

    async def publish(self, event: ReadingEvent, routing_key: str) -> None:
        if self._exchange is None:
            raise RuntimeError("Publisher is not connected")
        message = aio_pika.Message(
            event.model_dump_json().encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self._exchange.publish(message, routing_key=routing_key)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
