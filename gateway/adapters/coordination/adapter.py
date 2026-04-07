from typing import final, override

import structlog
from glide import ConditionalChange, ExpirySet, ExpiryType, GlideClient

from gateway.protocols.coordination.protocol import CoordinationProtocol

log = structlog.stdlib.get_logger("gateway.adapters.ValkeyAdapter")


@final
class CoordinationAdapter(CoordinationProtocol):
    def __init__(self, *, client: GlideClient) -> None:
        self._client = client

    @override
    async def ping(self) -> bool:
        try:
            result = await self._client.ping()
        except Exception as e:
            log.warning("ping failed", error=str(e))
            return False
        else:
            return result == b"PONG"

    @override
    async def incr_with_expire(self, key: str, expire_sec: int) -> int:
        try:
            count = await self._client.incr(key)
            if count == 1:
                _ = await self._client.expire(key, expire_sec)
        except Exception as e:
            log.warning("incr_with_expire failed", key=key, error=str(e))
            return 0
        else:
            return count

    @override
    async def set_nx(self, key: str, value: str, ttl_sec: int) -> bool:
        try:
            result = await self._client.set(
                key,
                value,
                conditional_set=ConditionalChange.ONLY_IF_DOES_NOT_EXIST,
                expiry=ExpirySet(ExpiryType.SEC, ttl_sec),
            )
        except Exception as e:
            log.warning("set_nx failed", key=key, error=str(e))
            return False
        else:
            return result is not None

    @override
    async def delete(self, key: str) -> None:
        try:
            _ = await self._client.delete([key])
        except Exception as e:
            log.warning("delete failed", key=key, error=str(e))
