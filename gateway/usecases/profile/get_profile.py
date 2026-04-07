from datetime import timedelta
from typing import final

import pydantic
import structlog

from gateway.domain.profile import Gender, PhotoInfo, Profile
from gateway.protocols.cache import CacheProtocol
from gateway.protocols.profile import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.usecases.GetProfile")

_CACHE_TTL = timedelta(minutes=5)


def _cache_key(telegram_id: int) -> str:
    return f"profile:{telegram_id}"


class _CachedProfile(pydantic.BaseModel):
    """Pydantic-обёртка для сериализации Profile в JSON кэш."""

    telegram_id: int
    profile_id: int
    name: str
    age: int
    city: str
    bio: str
    gender: str
    photos: list[dict[str, object]] = pydantic.Field(default_factory=list)
    latitude: float | None = None
    longitude: float | None = None

    @classmethod
    def from_domain(cls, p: Profile) -> "_CachedProfile":
        return cls(
            telegram_id=p.telegram_id,
            profile_id=p.profile_id,
            name=p.name,
            age=p.age,
            city=p.city,
            bio=p.bio,
            gender=p.gender.value,
            photos=[{"photo_id": ph.photo_id, "is_active": ph.is_active} for ph in p.photos],
            latitude=p.latitude,
            longitude=p.longitude,
        )

    def to_domain(self) -> Profile:
        return Profile(
            telegram_id=self.telegram_id,
            profile_id=self.profile_id,
            name=self.name,
            age=self.age,
            city=self.city,
            bio=self.bio,
            gender=Gender(self.gender),
            photos=[PhotoInfo(photo_id=int(ph["photo_id"]), is_active=bool(ph["is_active"])) for ph in self.photos],
            latitude=self.latitude,
            longitude=self.longitude,
        )


@final
class GetProfile:
    """Получить профиль пользователя (cache-aside: Valkey → gRPC)."""

    def __init__(self, *, profile_service: ProfileServiceProtocol, cache: CacheProtocol) -> None:
        self._profile_service = profile_service
        self._cache = cache

    async def execute(self, telegram_id: int) -> Profile | None:
        """Вернуть Profile или None если профиль не существует."""
        key = _cache_key(telegram_id)
        cached = await self._cache.get(key, unmarshal_as=_CachedProfile)
        if cached is not None:
            log.debug("profile cache hit", telegram_id=telegram_id)
            return cached.to_domain()

        profile = await self._profile_service.get_profile(telegram_id)
        if profile is None:
            return None

        await self._cache.set(key, _CachedProfile.from_domain(profile), ttl=_CACHE_TTL)
        log.debug("profile fetched from service, cached", telegram_id=telegram_id)
        return profile

    async def invalidate(self, telegram_id: int) -> None:
        """Инвалидировать кэш профиля."""
        await self._cache.delete(_cache_key(telegram_id))
