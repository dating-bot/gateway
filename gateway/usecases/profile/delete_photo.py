from typing import final

import structlog

from gateway.protocols.cache import CacheProtocol
from gateway.protocols.profile import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.usecases.DeletePhoto")


@final
class DeletePhoto:
    """Удалить фото профиля в profile-service."""

    def __init__(self, *, profile_service: ProfileServiceProtocol, cache: CacheProtocol) -> None:
        self._profile_service = profile_service
        self._cache = cache

    async def execute(self, telegram_id: int, photo_id: int) -> None:
        await self._profile_service.delete_photo(telegram_id, photo_id)
        await self._cache.delete(f"profile:{telegram_id}")
        log.info("photo deleted", telegram_id=telegram_id, photo_id=photo_id)
