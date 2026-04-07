from typing import final

import structlog

from gateway.protocols.cache import CacheProtocol
from gateway.protocols.profile import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.usecases.UploadPhoto")


@final
class UploadPhoto:
    """Загрузить фото профиля в profile-service."""

    def __init__(self, *, profile_service: ProfileServiceProtocol, cache: CacheProtocol) -> None:
        self._profile_service = profile_service
        self._cache = cache

    async def execute(self, telegram_id: int, data: bytes, content_type: str = "image/jpeg") -> int:
        """Возвращает photo_id."""
        photo_id = await self._profile_service.upload_photo(telegram_id, data, content_type)
        await self._cache.delete(f"profile:{telegram_id}")
        log.info("photo uploaded", telegram_id=telegram_id, photo_id=photo_id)
        return photo_id
