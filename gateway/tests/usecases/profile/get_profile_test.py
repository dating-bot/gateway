from collections.abc import Callable
from datetime import timedelta

import pytest

from gateway.protocols.profile.protocol import ProfileServiceProtocol
from gateway.usecases.profile.get_profile import GetProfile

_FOUND = ProfileServiceProtocol.GetProfileResult(
    found=True, profile_id=1, name="Alice", age=25, city="Moscow", bio="Hi"
)
_NOT_FOUND = ProfileServiceProtocol.GetProfileResult(found=False, profile_id=0, name="", age=0, city="", bio="")


class FakeProfileService:
    def __init__(self, result: ProfileServiceProtocol.GetProfileResult) -> None:
        self.calls: list[int] = []
        self._result = result

    async def get_profile(self, telegram_id: int) -> ProfileServiceProtocol.GetProfileResult:
        self.calls.append(telegram_id)
        return self._result

    async def create_profile(self, request: ProfileServiceProtocol.CreateProfileRequest) -> int:
        return 0

    async def update_profile(self, request: ProfileServiceProtocol.UpdateProfileRequest) -> bool:
        return False

    async def set_geo(self, request: ProfileServiceProtocol.SetGeoRequest) -> bool:
        return True

    async def upload_photo(self, request: ProfileServiceProtocol.UploadPhotoRequest) -> int:
        return 0


class FakeCache:
    def __init__(self, stored: ProfileServiceProtocol.GetProfileResult | None = None) -> None:
        self._store: dict[str, ProfileServiceProtocol.GetProfileResult] = (
            {"profile:42": stored} if stored is not None else {}
        )
        self.sets: list[tuple[str, object]] = []
        self.deletes: list[str] = []

    async def get[T](
        self,
        key: str,
        *,
        unmarshal_as: type[T] | None = None,
        unmarshal_using: Callable[[bytes], T] | None = None,
    ) -> T | None:
        return self._store.get(key)  # type: ignore[return-value]

    async def set[T](
        self,
        key: str,
        value: T,
        *,
        ttl: timedelta | None = None,
        marshal_using: Callable[[T], bytes] | None = None,
    ) -> None:
        self.sets.append((key, value))

    async def delete(self, key: str) -> None:
        self.deletes.append(key)
        self._store.pop(key, None)


@pytest.mark.asyncio
async def test_get_profile_cache_hit() -> None:
    service = FakeProfileService(_FOUND)
    cache = FakeCache(stored=_FOUND)
    usecase = GetProfile(profile_service=service, cache=cache)

    response = await usecase.execute(GetProfile.Request(telegram_id=42))

    assert response.profile == _FOUND
    assert service.calls == []  # сервис не вызывался


@pytest.mark.asyncio
async def test_get_profile_cache_miss_fetches_and_stores() -> None:
    service = FakeProfileService(_FOUND)
    cache = FakeCache()
    usecase = GetProfile(profile_service=service, cache=cache)

    response = await usecase.execute(GetProfile.Request(telegram_id=42))

    assert response.profile == _FOUND
    assert service.calls == [42]
    assert cache.sets == [("profile:42", _FOUND)]


@pytest.mark.asyncio
async def test_get_profile_not_found_does_not_cache() -> None:
    service = FakeProfileService(_NOT_FOUND)
    cache = FakeCache()
    usecase = GetProfile(profile_service=service, cache=cache)

    response = await usecase.execute(GetProfile.Request(telegram_id=99))

    assert response.profile is None
    assert cache.sets == []
