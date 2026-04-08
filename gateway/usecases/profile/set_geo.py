from typing import final

import structlog

from gateway.protocols.cache import CacheProtocol
from gateway.protocols.profile import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.usecases.SetGeo")


@final
class SetGeo:
    def __init__(self, *, profile_service: ProfileServiceProtocol, cache: CacheProtocol) -> None:
        self._profile_service = profile_service
        self._cache = cache

    async def execute(self, telegram_id: int, latitude: float, longitude: float) -> None:
        await self._profile_service.set_geo(telegram_id, latitude, longitude)
        await self._cache.delete(f"profile:{telegram_id}")
        log.info("geo updated", telegram_id=telegram_id, latitude=latitude, longitude=longitude)
