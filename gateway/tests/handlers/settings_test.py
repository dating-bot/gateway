# ruff: noqa: INP001

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gateway.app.telegram.handlers.preferences import (
    handle_settings_profile_pause,
    handle_settings_profile_resume,
    handle_settings_search_age,
    handle_settings_search_distance,
    handle_settings_search_gender,
)
from gateway.domain.profile import Gender, Profile
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.protocols.profile import ProfileServiceProtocol


def _query(user_id: int = 101) -> SimpleNamespace:
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        answer=AsyncMock(),
        message=SimpleNamespace(answer=AsyncMock()),
    )


def _profile(telegram_id: int) -> Profile:
    return Profile(
        telegram_id=telegram_id,
        profile_id=telegram_id,
        name="User",
        age=25,
        city="City",
        bio="Bio",
        gender=Gender.MALE,
        photos=[],
    )


@pytest.mark.asyncio
async def test_settings_profile_pause_sets_flag() -> None:
    query = _query(700)
    resolved = ResolvedCallback(handler_id="handle_settings_profile_pause")
    get_profile = AsyncMock()
    get_profile.execute.return_value = _profile(700)
    profile_service = AsyncMock()
    profile_service.get_profile_by_id.return_value = _profile(700)
    cache = AsyncMock()
    cache.get.return_value = 1

    await handle_settings_profile_pause(query, resolved, get_profile, profile_service, cache)

    cache.set.assert_awaited_once()
    assert cache.set.await_args.args[0] == "profile:paused:700"
    query.message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_settings_profile_resume_clears_flag() -> None:
    query = _query(701)
    resolved = ResolvedCallback(handler_id="handle_settings_profile_resume")
    get_profile = AsyncMock()
    get_profile.execute.return_value = _profile(701)
    profile_service = AsyncMock()
    profile_service.get_profile_by_id.return_value = _profile(701)
    cache = AsyncMock()
    cache.get.return_value = None

    await handle_settings_profile_resume(query, resolved, get_profile, profile_service, cache)

    cache.delete.assert_awaited_once_with("profile:paused:701")
    query.message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_settings_resume_shows_paused_when_profile_inactive() -> None:
    query = _query(702)
    resolved = ResolvedCallback(handler_id="handle_settings_profile_resume")
    get_profile = AsyncMock()
    get_profile.execute.return_value = _profile(702)
    profile_service = AsyncMock()
    inactive = _profile(702)
    inactive = Profile(
        telegram_id=inactive.telegram_id,
        profile_id=inactive.profile_id,
        name=inactive.name,
        age=inactive.age,
        city=inactive.city,
        bio=inactive.bio,
        gender=inactive.gender,
        photos=inactive.photos,
        is_active=False,
    )
    profile_service.get_profile_by_id.return_value = inactive
    cache = AsyncMock()
    cache.get.return_value = None

    await handle_settings_profile_resume(query, resolved, get_profile, profile_service, cache)

    text = query.message.answer.await_args.args[0]
    assert "Статус анкеты: ⏸ На паузе" in text


@pytest.mark.asyncio
async def test_settings_search_gender_updates_preferences() -> None:
    query = _query(900)
    resolved = ResolvedCallback(handler_id="handle_settings_search_gender", path_params={"gender": "female"})
    profile_service = AsyncMock()
    profile_service.get_preferences.return_value = ProfileServiceProtocol.Preferences(
        gender_pref=Gender.ANY,
        age_min=18,
        age_max=30,
        max_distance_km=50,
    )

    await handle_settings_search_gender(query, resolved, profile_service)

    profile_service.set_preferences.assert_awaited_once()
    request = profile_service.set_preferences.await_args.args[0]
    assert request.gender_pref == Gender.FEMALE
    assert request.age_min == 18
    assert request.age_max == 30
    assert request.max_distance_km == 50


@pytest.mark.asyncio
async def test_settings_search_age_updates_preferences() -> None:
    query = _query(901)
    resolved = ResolvedCallback(handler_id="handle_settings_search_age", path_params={"age": "26-35"})
    profile_service = AsyncMock()
    profile_service.get_preferences.return_value = ProfileServiceProtocol.Preferences(
        gender_pref=Gender.MALE,
        age_min=18,
        age_max=30,
        max_distance_km=50,
    )

    await handle_settings_search_age(query, resolved, profile_service)

    request = profile_service.set_preferences.await_args.args[0]
    assert request.age_min == 26
    assert request.age_max == 35
    assert request.gender_pref == Gender.MALE


@pytest.mark.asyncio
async def test_settings_search_distance_updates_preferences() -> None:
    query = _query(902)
    resolved = ResolvedCallback(handler_id="handle_settings_search_distance", path_params={"km": "100"})
    profile_service = AsyncMock()
    profile_service.get_preferences.return_value = ProfileServiceProtocol.Preferences(
        gender_pref=Gender.ANY,
        age_min=18,
        age_max=99,
        max_distance_km=50,
    )

    await handle_settings_search_distance(query, resolved, profile_service)

    request = profile_service.set_preferences.await_args.args[0]
    assert request.max_distance_km == 100
    assert request.age_min == 18
    assert request.age_max == 99
