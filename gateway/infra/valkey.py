from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import timedelta

from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.redis import RedisStorage
from glide import GlideClient, GlideClientConfiguration, NodeAddress
from pydantic import BaseModel, Field


class ValkeyConfig(BaseModel):
    """Configuration for Valkey/Redis cache."""

    host: str = Field(default="localhost", description="Valkey хост")
    port: int = Field(default=6379, description="Valkey порт")
    use_tls: bool = Field(default=False, description="TLS соединение")
    cache_ttl: timedelta = Field(default=timedelta(minutes=10), description="TTL кэша")
    rate_limit_per_minute: int = Field(default=30, description="Максимум действий в минуту на пользователя")
    rate_limit_window_seconds: int = Field(default=60, description="Окно rate limit в секундах")
    user_lock_ttl_sec: int = Field(default=5, description="TTL блокировки пользователя в секундах")

    @property
    def url(self) -> str:
        scheme = "rediss" if self.use_tls else "redis"
        return f"{scheme}://{self.host}:{self.port}"


@dataclass(slots=True)
class ValkeyRuntime:
    storage: BaseStorage

    async def close(self) -> None:
        close = getattr(self.storage, "close", None)
        if close is not None:
            await close()


def provide_valkey_runtime(config: ValkeyConfig) -> ValkeyRuntime:
    """FSM storage (Redis) + lifecycle handle; same Valkey as Glide."""
    storage = RedisStorage.from_url(config.url)
    return ValkeyRuntime(storage=storage)


async def provide_glide_client(config: ValkeyConfig) -> AsyncGenerator[GlideClient]:
    """Glide client with lifecycle management (coordination + cache adapters)."""
    client = await GlideClient.create(
        GlideClientConfiguration(
            addresses=[NodeAddress(config.host, config.port)],
            use_tls=config.use_tls,
            request_timeout=5000,
        )
    )
    try:
        yield client
    finally:
        await client.close()
