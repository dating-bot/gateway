from typing import final, override

import structlog
from glide import ConditionalChange, ExpirySet, ExpiryType, GlideClient

from gateway.protocols.coordination import CoordinationProtocol

log = structlog.stdlib.get_logger("gateway.adapters.ValkeyCoordinationAdapter")


@final
class ValkeyCoordinationAdapter(CoordinationProtocol):
    """Реализация CoordinationProtocol через GlideClient (Valkey/Redis)."""

    def __init__(self, *, client: GlideClient) -> None:
        self._client = client

    @override
    async def ping(self) -> bool:
        try:
            result = await self._client.ping()
            return result in (b"PONG", "PONG")
        except Exception:
            log.exception("ping failed")
            return False

    @override
    async def incr_with_expire(self, key: str, expire_sec: int) -> int:
        """INCR + EXPIRE если счётчик новый. Возвращает новое значение."""
        count = await self._client.incr(key)
        if count == 1:
            _ = await self._client.expire(key, expire_sec)
        return count

    @override
    async def set_nx(self, key: str, value: str, ttl_sec: int) -> bool:
        """SET key value NX EX ttl — атомарный distributed lock.

        Возвращает True если lock успешно получен.
        """
        result = await self._client.set(
            key,
            value,
            conditional_set=ConditionalChange.ONLY_IF_DOES_NOT_EXIST,
            expiry=ExpirySet(ExpiryType.SEC, ttl_sec),
        )
        return result is not None

    @override
    async def delete(self, key: str) -> None:
        _ = await self._client.delete([key])
