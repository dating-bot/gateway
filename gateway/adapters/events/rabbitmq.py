from typing import final, override

import aio_pika
import structlog

from gateway.infra.rabbitmq import RabbitMQConfig
from gateway.protocols.events import EventPublisherProtocol

log = structlog.stdlib.get_logger("gateway.adapters.RabbitMQPublisher")


@final
class RabbitMQPublisherAdapter(EventPublisherProtocol):
    def __init__(self, config: RabbitMQConfig) -> None:
        self._config = config
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def initialize(self) -> None:
        self._connection = await aio_pika.connect_robust(self._config.url)
        self._channel = await self._connection.channel()
        log.info("rabbitmq publisher connected", url=self._config.url)

    async def publish(self, routing_key: str, body: bytes, delivery_mode: int = 2) -> None:
        if self._channel is None:
            await self.initialize()

        message = aio_pika.Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT if delivery_mode == 2 else aio_pika.DeliveryMode.NOT_PERSISTENT,
        )
        await self._channel.default_exchange.publish(message, routing_key=routing_key)
        log.debug("message published", routing_key=routing_key, size=len(body))

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            log.info("rabbitmq publisher closed")