from typing import final

import pydantic
import structlog

from gateway.protocols.cache.protocol import CacheProtocol

log = structlog.stdlib.get_logger("gateway.usecases.profile.InvalidateProfile")

_CACHE_KEY = "profile:{}"


@final
class InvalidateProfile:
    def __init__(self, *, cache: CacheProtocol) -> None:
        self._cache = cache

    class Request(pydantic.BaseModel):
        telegram_id: int

    async def execute(self, request: Request) -> None:
        key = _CACHE_KEY.format(request.telegram_id)
        await self._cache.delete(key)
        log.debug("profile cache invalidated", telegram_id=request.telegram_id)
