from typing import final

import pydantic
import structlog

from gateway.protocols.cache import CacheProtocol
from gateway.protocols.profile import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.usecases.UpdateProfile")


@final
class UpdateProfile:
    """Обновить данные профиля пользователя."""

    def __init__(self, *, profile_service: ProfileServiceProtocol, cache: CacheProtocol) -> None:
        self._profile_service = profile_service
        self._cache = cache

    class Request(pydantic.BaseModel):
        telegram_id: int
        name: str
        age: int
        city: str
        bio: str

    async def execute(self, request: "UpdateProfile.Request") -> None:
        await self._profile_service.update_profile(
            ProfileServiceProtocol.UpdateRequest(
                telegram_id=request.telegram_id,
                name=request.name,
                age=request.age,
                city=request.city,
                bio=request.bio,
            )
        )
        await self._cache.delete(f"profile:{request.telegram_id}")
        log.info("profile updated", telegram_id=request.telegram_id)
