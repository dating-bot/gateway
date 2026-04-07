from collections.abc import Callable
from datetime import timedelta
from typing import cast, final, override

import structlog
from glide import ExpirySet, ExpiryType, GlideClient

from gateway.infra.valkey import ValkeyConfig
from gateway.protocols.cache.protocol import CacheProtocol
from gateway.utils.serialization import deserialize, serialize

log = structlog.stdlib.get_logger("gateway.adapters.ValkeyCacheAdapter")


@final
class ValkeyCacheAdapter(CacheProtocol):
    def __init__(self, *, client: GlideClient, config: ValkeyConfig) -> None:
        self._client = client
        self._cfg = config

    @override
    async def get[T](  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        key: str,
        *,
        unmarshal_as: type[T] | None = None,
        unmarshal_using: Callable[[bytes], T] | None = None,
    ) -> T | None:
        try:
            raw_bytes = await self._client.get(key)
            if raw_bytes is None:
                return None

            if unmarshal_as is None and unmarshal_using is None:
                return cast("T", raw_bytes)

            if unmarshal_using is not None:
                return deserialize(raw_bytes, using=unmarshal_using)

            if unmarshal_as is not None:
                return deserialize(raw_bytes, to=unmarshal_as)

        except Exception as e:
            log.warning("failed to get value from cache", key=key, error=str(e))
            return None
        else:
            log.warning("no valid way to deserialize value was found", key=key)
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
            if ttl is None:
                ttl = self._cfg.cache_ttl

            value_bytes = value if isinstance(value, bytes) else serialize(value, using=marshal_using)
            expiry = ExpirySet(ExpiryType.SEC, int(ttl.total_seconds()))
            _ = await self._client.set(key, value_bytes, expiry=expiry)
        except Exception as e:
            log.warning("failed to set value to cache", key=key, error=str(e))

    @override
    async def delete(self, key: str) -> None:
        try:
            _ = await self._client.delete([key])
        except Exception as e:
            log.warning("failed to delete value from cache", key=key, error=str(e))
