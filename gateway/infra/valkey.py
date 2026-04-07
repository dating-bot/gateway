from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import timedelta

from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.redis import RedisStorage
from glide import GlideClient, GlideClientConfiguration, NodeAddress
from pydantic import AliasChoices, BaseModel, Field


class ValkeyConfig(BaseModel):
    """Valkey: один хост, разные логические БД (как в docs: /0 FSM, /1 coordination+cache)."""

    host: str = Field(default="localhost", description="Valkey хост")
    port: int = Field(default=6379, description="Valkey порт")
    use_tls: bool = Field(default=False, description="TLS соединение")
    fsm_database: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices("fsm_database", "fsm_db"),
        description="БД aiogram FSM (RedisStorage)",
    )
    coordination_database: int = Field(
        default=1,
        ge=0,
        description="БД Glide: rate limit, lock, кэш-адаптер",
    )
    cache_ttl: timedelta = Field(default=timedelta(minutes=10), description="TTL кэша")
    rate_limit_per_minute: int = Field(default=30, description="Максимум действий в минуту на пользователя")
    rate_limit_window_seconds: int = Field(default=60, description="Окно rate limit в секундах")
    user_lock_ttl_sec: int = Field(default=5, description="TTL блокировки пользователя в секундах")

    def _base_url(self) -> str:
        scheme = "rediss" if self.use_tls else "redis"
        return f"{scheme}://{self.host}:{self.port}"

    @property
    def fsm_url(self) -> str:
        """redis://host:port/{fsm_database} — изолированно от coordination/cache."""
        return f"{self._base_url()}/{self.fsm_database}"

    @property
    def coordination_url(self) -> str:
        """Тот же хост, другая логическая БД (для отладки и внешних клиентов)."""
        return f"{self._base_url()}/{self.coordination_database}"


@dataclass(slots=True)
class ValkeyRuntime:
    storage: BaseStorage

    async def close(self) -> None:
        close = getattr(self.storage, "close", None)
        if close is not None:
            await close()


def provide_valkey_runtime(config: ValkeyConfig) -> ValkeyRuntime:
    """FSM storage на отдельной логической БД от Glide (см. fsm_database)."""
    storage = RedisStorage.from_url(config.fsm_url)
    return ValkeyRuntime(storage=storage)


async def provide_glide_client(config: ValkeyConfig) -> AsyncGenerator[GlideClient]:
    """Glide на coordination_database (rate limit / lock / cache), не на FSM."""
    client = await GlideClient.create(
        GlideClientConfiguration(
            addresses=[NodeAddress(config.host, config.port)],
            use_tls=config.use_tls,
            database_id=config.coordination_database,
            request_timeout=5000,
        )
    )
    try:
        yield client
    finally:
        await client.close()
