from shared.events import TELEMETRY_IOT_QUEUE
from shared.rabbitmq import EventCallback, RabbitMQConsumer


class Consumer:
    """Consumes telemetry IoT events from RabbitMQ and hands each message body to a callback."""

    def __init__(self, url: str, on_event: EventCallback):
        self._inner = RabbitMQConsumer(
            url, TELEMETRY_IOT_QUEUE, on_event,
            task_name="telemetry-consumer",
        )

    async def start(self) -> None:
        """Connect and start the consume loop as a background task."""
        await self._inner.start()

    async def stop(self) -> None:
        """Cancel the consume loop and close the RabbitMQ connection."""
        await self._inner.stop()
