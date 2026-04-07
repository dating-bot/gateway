from collections.abc import Callable
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from grpclib.const import Status
from grpclib.exceptions import GRPCError

from gateway.protocols.cache.protocol import CacheProtocol
from gateway.protocols.profile.protocol import ProfileServiceProtocol
from gateway.usecases.profile.create_profile import CreateProfile
from gateway.usecases.profile.errors import DuplicateProfileError, ProfileNotFoundForMutationError
from gateway.usecases.profile.get_profile import GetProfile
from gateway.usecases.profile.invalidate_profile import InvalidateProfile
from gateway.usecases.profile.update_profile import UpdateProfile

_FOUND = ProfileServiceProtocol.GetProfileResult(
    found=True,
    profile_id=7,
    name="Alice",
    age=25,
    city="Moscow",
    bio="Hi",
)


class FakeCache:
    def __init__(self, stored: ProfileServiceProtocol.GetProfileResult | None = None) -> None:
        self._store: dict[str, ProfileServiceProtocol.GetProfileResult] = (
            {"profile:42": stored} if stored is not None else {}
        )
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
        self._store[key] = value  # type: ignore[assignment]

    async def delete(self, key: str) -> None:
        self.deletes.append(key)
        self._store.pop(key, None)


@pytest.mark.asyncio
async def test_create_profile_then_get_profile_refreshes() -> None:
    svc = AsyncMock(spec=ProfileServiceProtocol)
    svc.create_profile = AsyncMock(return_value=7)
    svc.get_profile = AsyncMock(return_value=_FOUND)

    cache: CacheProtocol = FakeCache()
    get_profile = GetProfile(profile_service=svc, cache=cache)
    usecase = CreateProfile(profile_service=svc, get_profile=get_profile)

    response = await usecase.execute(
        CreateProfile.Request(
            telegram_id=42,
            name="Alice",
            age=25,
            city="Moscow",
            bio="Hi",
            gender=1,
        ),
    )

    assert response.profile == _FOUND
    svc.create_profile.assert_awaited_once()
    svc.get_profile.assert_awaited_once_with(42)


@pytest.mark.asyncio
async def test_create_profile_duplicate_raises() -> None:
    svc = AsyncMock(spec=ProfileServiceProtocol)
    svc.create_profile = AsyncMock(
        side_effect=GRPCError(Status.ALREADY_EXISTS, "exists"),
    )

    cache: CacheProtocol = FakeCache()
    get_profile = GetProfile(profile_service=svc, cache=cache)
    usecase = CreateProfile(profile_service=svc, get_profile=get_profile)

    with pytest.raises(DuplicateProfileError):
        await usecase.execute(
            CreateProfile.Request(
                telegram_id=42,
                name="A",
                age=20,
                city="X",
                bio="",
                gender=1,
            ),
        )


@pytest.mark.asyncio
async def test_update_profile_invalidates_and_refetches() -> None:
    svc = AsyncMock(spec=ProfileServiceProtocol)
    svc.update_profile = AsyncMock(return_value=True)
    svc.get_profile = AsyncMock(return_value=_FOUND)

    cache: CacheProtocol = FakeCache()
    get_profile = GetProfile(profile_service=svc, cache=cache)
    invalidate = InvalidateProfile(cache=cache)
    usecase = UpdateProfile(
        profile_service=svc,
        invalidate_profile=invalidate,
        get_profile=get_profile,
    )

    response = await usecase.execute(
        UpdateProfile.Request(
            telegram_id=42,
            name="Bob",
            age=30,
            city="SPb",
            bio="Hey",
        ),
    )

    assert response.profile == _FOUND
    svc.update_profile.assert_awaited_once()
    assert isinstance(cache, FakeCache)
    assert cache.deletes == ["profile:42"]
    svc.get_profile.assert_awaited_once_with(42)


@pytest.mark.asyncio
async def test_update_profile_not_found_raises() -> None:
    svc = AsyncMock(spec=ProfileServiceProtocol)
    svc.update_profile = AsyncMock(side_effect=GRPCError(Status.NOT_FOUND, "nf"))

    cache: CacheProtocol = FakeCache()
    get_profile = GetProfile(profile_service=svc, cache=cache)
    invalidate = InvalidateProfile(cache=cache)
    usecase = UpdateProfile(
        profile_service=svc,
        invalidate_profile=invalidate,
        get_profile=get_profile,
    )

    with pytest.raises(ProfileNotFoundForMutationError):
        await usecase.execute(
            UpdateProfile.Request(
                telegram_id=99,
                name="A",
                age=20,
                city="X",
                bio="",
            ),
        )
