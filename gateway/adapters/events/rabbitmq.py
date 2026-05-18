from typing import final
from uuid import uuid4

import aio_pika
import structlog
import structlog.contextvars

from gateway.infra.rabbitmq import RabbitMQConfig
from gateway.infra.tracing import current_trace_id, inject_trace_headers
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

    async def publish(
        self,
        routing_key: str,
        body: bytes,
        delivery_mode: int = 2,
        headers: dict[str, object] | None = None,
    ) -> None:
        if self._channel is None:
            await self.initialize()

        current = structlog.contextvars.get_contextvars()
        trace_id = str(current.get("trace_id") or current_trace_id() or uuid4().hex)
        merged_headers = inject_trace_headers({"trace_id": trace_id, **(headers or {})})

        message = aio_pika.Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            if delivery_mode == 2
            else aio_pika.DeliveryMode.NOT_PERSISTENT,
            headers=merged_headers,
        )
        _ = await self._channel.default_exchange.publish(message, routing_key=routing_key)
        log.debug("message published", routing_key=routing_key, size=len(body), trace_id=trace_id)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            log.info("rabbitmq publisher closed")
