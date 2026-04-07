from collections.abc import AsyncGenerator

from glide import GlideClient, GlideClientConfiguration, NodeAddress
from pydantic import BaseModel, Field


class ValkeyConfig(BaseModel):
    host: str = Field(default="localhost", description="Valkey host")
    port: int = Field(default=6379, description="Valkey port")
    use_tls: bool = Field(default=False, description="Использовать TLS")
    fsm_db: int = Field(default=0, description="DB для aiogram FSM (redis-py)")
    cache_db: int = Field(default=1, description="DB для кэша и rate limit (GlideClient)")
    user_lock_ttl_sec: int = Field(default=5, description="TTL распределённого лока юзера (сек)")
    rate_limit_per_minute: int = Field(default=30, description="Макс. действий в минуту на юзера")
    profile_cache_ttl_sec: int = Field(default=300, description="TTL кэша профиля (сек)")


async def provide_glide_client(config: ValkeyConfig) -> AsyncGenerator[GlideClient]:
    """GlideClient (Rust-based) для кэша и coordination (rate limit, lock)."""
    client = await GlideClient.create(
        GlideClientConfiguration(
            addresses=[NodeAddress(config.host, config.port)],
            use_tls=config.use_tls,
            database_id=config.cache_db,
            request_timeout=5000,
        )
    )
    try:
        yield client
    finally:
        await client.close()
