from typing import final

import pydantic
import structlog

from gateway.domain.profile import Gender
from gateway.protocols.cache import CacheProtocol
from gateway.protocols.profile import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.usecases.CreateProfile")


@final
class CreateProfile:
    """Создать профиль пользователя через profile-service."""

    def __init__(self, *, profile_service: ProfileServiceProtocol, cache: CacheProtocol) -> None:
        self._profile_service = profile_service
        self._cache = cache

    class Request(pydantic.BaseModel):
        telegram_id: int
        name: str
        age: int
        city: str
        bio: str
        gender: Gender
        latitude: float | None = None
        longitude: float | None = None

    async def execute(self, request: "CreateProfile.Request") -> int:
        """Создать профиль, инвалидировать кэш. Возвращает profile_id."""
        profile_id = await self._profile_service.create_profile(
            ProfileServiceProtocol.CreateRequest(
                telegram_id=request.telegram_id,
                name=request.name,
                age=request.age,
                city=request.city,
                bio=request.bio,
                gender=request.gender,
                latitude=request.latitude,
                longitude=request.longitude,
            )
        )
        await self._cache.delete(f"profile:{request.telegram_id}")
        log.info("profile created", telegram_id=request.telegram_id, profile_id=profile_id)
        return profile_id
