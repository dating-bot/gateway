from typing import Protocol, final


@final
class EventPublisherProtocol(Protocol):
    async def publish(
        self,
        routing_key: str,
        body: bytes,
        delivery_mode: int = 2,
        headers: dict[str, object] | None = None,
    ) -> None:
        """Publish message to RabbitMQ."""
        raise NotImplementedError
