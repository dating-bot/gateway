from collections.abc import AsyncGenerator

import aio_pika
import aio_pika.abc
from pydantic import BaseModel


class RabbitMQConfig(BaseModel):
    host: str
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtualhost: str = "/"

    @property
    def url(self) -> str:
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}{self.virtualhost}"


async def provide_rabbitmq_connection(
    config: RabbitMQConfig,
) -> AsyncGenerator[aio_pika.abc.AbstractRobustConnection]:
    """Создаёт robust connection к RabbitMQ."""
    connection = await aio_pika.connect_robust(config.url)
    try:
        yield connection
    finally:
        await connection.close()
