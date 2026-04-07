from datetime import timedelta
from typing import final

import pydantic
import structlog

from gateway.protocols.cache.protocol import CacheProtocol
from gateway.protocols.profile.protocol import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.usecases.profile.GetProfile")

_CACHE_TTL = timedelta(minutes=5)
_CACHE_KEY = "profile:{}"


@final
class GetProfile:
    def __init__(
        self,
        *,
        profile_service: ProfileServiceProtocol,
        cache: CacheProtocol,
    ) -> None:
        self._profile_service = profile_service
        self._cache = cache

    class Request(pydantic.BaseModel):
        telegram_id: int

    class Response(pydantic.BaseModel):
        profile: ProfileServiceProtocol.GetProfileResult | None

    async def execute(self, request: Request) -> Response:
        key = _CACHE_KEY.format(request.telegram_id)

        cached = await self._cache.get(key, unmarshal_as=ProfileServiceProtocol.GetProfileResult)
        if cached is not None:
            log.debug("profile cache hit", telegram_id=request.telegram_id)
            return self.Response(profile=cached)

        result = await self._profile_service.get_profile(request.telegram_id)
        if not result.found:
            return self.Response(profile=None)

        await self._cache.set(key, result, ttl=_CACHE_TTL)
        return self.Response(profile=result)
