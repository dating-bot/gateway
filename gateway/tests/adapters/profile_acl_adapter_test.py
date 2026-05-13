# ruff: noqa: INP001

from unittest.mock import AsyncMock

import pytest

from gateway.adapters.acl.profile_acl_adapter import ProfileAclAdapter
from gateway.domain.profile import Gender, Profile


def _profile(user_id: int) -> Profile:
    return Profile(
        telegram_id=user_id,
        profile_id=user_id,
        name="User",
        age=25,
        city="City",
        bio="Bio",
        gender=Gender.FEMALE,
        photos=[],
    )


@pytest.mark.asyncio
async def test_acl_denies_active_when_profile_paused() -> None:
    profile_service = AsyncMock()
    profile_service.get_profile.return_value = _profile(1001)
    cache = AsyncMock()
    cache.get.return_value = 1

    acl = ProfileAclAdapter(profile_service=profile_service, cache=cache)

    allowed = await acl.check(1001, {"active": True})

    assert allowed is False
