# ruff: noqa: INP001

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gateway.app.telegram.handlers.like_skip import handle_like, handle_skip, handle_super_like, handle_undo
from gateway.domain.profile import Gender, Profile, SubscriptionTier
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.infra.telegram import TelegramConfig


def _query_with_user(user_id: int) -> SimpleNamespace:
    bot = AsyncMock()
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        bot=bot,
        answer=AsyncMock(),
        message=SimpleNamespace(answer=AsyncMock(), chat=SimpleNamespace(id=user_id), bot=bot),
    )


def _config(**overrides: object) -> TelegramConfig:
    base = {
        "token": "test-token",
        "free_like_daily_limit": 50,
        "free_super_like_daily_limit": 1,
        "free_undo_daily_limit": 3,
    }
    base.update(overrides)
    return TelegramConfig(**base)


def _profile(telegram_id: int, *, premium: bool = False) -> Profile:
    tier = SubscriptionTier.PREMIUM if premium else SubscriptionTier.FREE
    expires = 2_200_000_000 if premium else None
    return Profile(
        telegram_id=telegram_id,
        profile_id=telegram_id,
        name="User",
        age=25,
        city="Moscow",
        bio="Bio",
        gender=Gender.FEMALE,
        photos=[],
        subscription_tier=tier,
        subscription_expires_at_seconds=expires,
    )


@pytest.mark.asyncio
async def test_handle_like_publishes_interaction_event() -> None:
    query = _query_with_user(101)
    resolved = ResolvedCallback(handler_id="handle_like", path_params={"profile_id": "202"})
    publisher = AsyncMock()
    cache = AsyncMock()
    cache.get.return_value = None
    get_profile = AsyncMock()
    get_profile.execute.return_value = _profile(101, premium=False)
    profile_service = AsyncMock()
    profile_service.get_profile_by_id.return_value = None
    profile_service.get_profile.return_value = None
    ranking_service = AsyncMock()
    ranking_service.get_next_candidate.return_value = (202, 5)

    await handle_like(query, resolved, publisher, cache, get_profile, profile_service, ranking_service, _config())

    assert publisher.publish.await_count == 2
    published = [call.args for call in publisher.publish.await_args_list]
    assert ("interaction.like", b'{"liker_telegram_id": 101, "liked_telegram_id": 202, "status": "liked"}') in published
    assert ("ranking.interaction.like", b'{"liker_telegram_id": 101, "liked_telegram_id": 202}') in published
    query.answer.assert_awaited_once_with("❤️")
    query.message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_like_blocks_when_free_daily_limit_reached() -> None:
    query = _query_with_user(101)
    resolved = ResolvedCallback(handler_id="handle_like", path_params={"profile_id": "202"})
    publisher = AsyncMock()
    cache = AsyncMock()
    cache.get.return_value = 50
    get_profile = AsyncMock()
    get_profile.execute.return_value = _profile(101, premium=False)
    profile_service = AsyncMock()
    ranking_service = AsyncMock()

    await handle_like(query, resolved, publisher, cache, get_profile, profile_service, ranking_service, _config())

    publisher.publish.assert_not_awaited()
    query.message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_super_like_publishes_superliked_status() -> None:
    query = _query_with_user(303)
    resolved = ResolvedCallback(handler_id="handle_super_like", path_params={"profile_id": "404"})
    publisher = AsyncMock()
    cache = AsyncMock()
    cache.get.return_value = None
    get_profile = AsyncMock()
    get_profile.execute.return_value = _profile(303, premium=False)
    profile_service = AsyncMock()
    profile_service.get_profile_by_id.return_value = None
    profile_service.get_profile.return_value = None
    ranking_service = AsyncMock()
    ranking_service.get_next_candidate.return_value = (404, 3)

    await handle_super_like(query, resolved, publisher, cache, get_profile, profile_service, ranking_service, _config())

    published = [call.args for call in publisher.publish.await_args_list]
    assert (
        "interaction.like",
        b'{"liker_telegram_id": 303, "liked_telegram_id": 404, "status": "superliked"}',
    ) in published
    assert ("ranking.interaction.like", b'{"liker_telegram_id": 303, "liked_telegram_id": 404}') in published
    query.answer.assert_awaited_once_with("⭐")


@pytest.mark.asyncio
async def test_handle_super_like_premium_has_no_daily_limit() -> None:
    query = _query_with_user(303)
    resolved = ResolvedCallback(handler_id="handle_super_like", path_params={"profile_id": "404"})
    publisher = AsyncMock()
    cache = AsyncMock()
    cache.get.return_value = 99
    get_profile = AsyncMock()
    get_profile.execute.return_value = _profile(303, premium=True)
    profile_service = AsyncMock()
    profile_service.get_profile_by_id.return_value = None
    profile_service.get_profile.return_value = None
    ranking_service = AsyncMock()
    ranking_service.get_next_candidate.return_value = (404, 3)

    await handle_super_like(query, resolved, publisher, cache, get_profile, profile_service, ranking_service, _config())

    assert publisher.publish.await_count == 2


@pytest.mark.asyncio
async def test_handle_skip_publishes_interaction_event() -> None:
    query = _query_with_user(303)
    resolved = ResolvedCallback(handler_id="handle_skip", path_params={"profile_id": "404"})
    publisher = AsyncMock()
    cache = AsyncMock()
    cache.get.return_value = None
    get_profile = AsyncMock()
    get_profile.execute.return_value = _profile(303, premium=False)
    profile_service = AsyncMock()
    profile_service.get_profile_by_id.return_value = None
    profile_service.get_profile.return_value = None
    ranking_service = AsyncMock()
    ranking_service.get_next_candidate.return_value = (404, 3)

    await handle_skip(query, resolved, publisher, cache, get_profile, profile_service, ranking_service)

    assert publisher.publish.await_count == 2
    assert cache.set.await_count == 3
    published = [call.args for call in publisher.publish.await_args_list]
    assert ("interaction.skip", b'{"actor_telegram_id": 303, "target_telegram_id": 404}') in published
    assert ("ranking.interaction.skip", b'{"actor_telegram_id": 303, "target_telegram_id": 404}') in published
    query.answer.assert_awaited_once_with("👎")
    query.message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_undo_restores_last_skipped_profile() -> None:
    query = _query_with_user(505)
    resolved = ResolvedCallback(handler_id="handle_undo", path_params={})
    publisher = AsyncMock()
    cache = AsyncMock()
    cache.get.side_effect = ["skip", 606, 0]
    profile_service = AsyncMock()
    profile_service.get_profile.side_effect = [
        _profile(505, premium=False),
        SimpleNamespace(
            profile_id=606,
            telegram_id=606,
            name="Restored User",
            age=27,
            city="Moscow",
            bio="Bio",
            gender=SimpleNamespace(value="female"),
            photos=[],
        ),
    ]

    await handle_undo(query, resolved, publisher, cache, profile_service, _config())

    publisher.publish.assert_awaited_once_with(
        "ranking.interaction.undo_skip",
        b'{"actor_telegram_id": 505, "target_telegram_id": 606}',
    )
    query.answer.assert_awaited_once_with("Анкета возвращена")
    query.bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_undo_blocks_when_free_daily_limit_reached() -> None:
    query = _query_with_user(505)
    resolved = ResolvedCallback(handler_id="handle_undo", path_params={})
    publisher = AsyncMock()
    cache = AsyncMock()
    cache.get.side_effect = ["skip", 606, 3]
    profile_service = AsyncMock()
    profile_service.get_profile.return_value = _profile(505, premium=False)

    await handle_undo(query, resolved, publisher, cache, profile_service, _config())

    publisher.publish.assert_not_awaited()
    query.message.answer.assert_awaited_once()
