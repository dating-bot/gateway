from collections.abc import Callable
from datetime import timedelta
from typing import final, override

import structlog
from glide import ExpirySet, ExpiryType, GlideClient
from pydantic import TypeAdapter

from gateway.infra.valkey import ValkeyConfig
from gateway.protocols.cache import CacheProtocol

log = structlog.stdlib.get_logger("gateway.adapters.ValkeyCacheAdapter")


def _build_serializer[T](t: type[T]) -> Callable[[T], bytes]:
    adapter: TypeAdapter[T] = TypeAdapter(t)
    return lambda v: adapter.dump_json(v, exclude_none=False)


def _build_deserializer[T](t: type[T]) -> Callable[[bytes], T]:
    adapter: TypeAdapter[T] = TypeAdapter(t)
    return lambda raw: adapter.validate_json(raw)


@final
class ValkeyCacheAdapter(CacheProtocol):
    """Кэш через GlideClient. Сериализация: Pydantic JSON."""

    def __init__(self, *, client: GlideClient, config: ValkeyConfig) -> None:
        self._client = client
        self._default_ttl = timedelta(seconds=config.profile_cache_ttl_sec)

    @override
    async def get[T](  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        key: str,
        *,
        unmarshal_as: type[T] | None = None,
        unmarshal_using: Callable[[bytes], T] | None = None,
    ) -> T | None:
        try:
            raw = await self._client.get(key)
            if raw is None:
                return None
            if unmarshal_as is None and unmarshal_using is None:
                return raw  # type: ignore[return-value]
            deserialize = unmarshal_using or _build_deserializer(unmarshal_as)  # type: ignore[arg-type]
            return deserialize(raw if isinstance(raw, bytes) else raw.encode())
        except Exception:
            log.warning("cache get failed", key=key)
            return None

    @override
    async def set[T](
        self,
        key: str,
        value: T,
        *,
        ttl: timedelta | None = None,
        marshal_using: Callable[[T], bytes] | None = None,
    ) -> None:
        try:
            effective_ttl = ttl or self._default_ttl
            if isinstance(value, bytes):
                data = value
            else:
                serialize = marshal_using or _build_serializer(type(value))
                data = serialize(value)
            expiry = ExpirySet(ExpiryType.SEC, int(effective_ttl.total_seconds()))
            await self._client.set(key, data, expiry=expiry)
        except Exception:
            log.warning("cache set failed", key=key)

    @override
    async def delete(self, key: str) -> None:
        try:
            await self._client.delete([key])
        except Exception:
            log.warning("cache delete failed", key=key)
