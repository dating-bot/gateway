from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gateway.app.telegram.handlers.like_skip import handle_like, handle_skip, handle_undo
from gateway.domain.resolved_callback import ResolvedCallback


def _query_with_user(user_id: int) -> SimpleNamespace:
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        bot=AsyncMock(),
        answer=AsyncMock(),
        message=SimpleNamespace(answer=AsyncMock(), chat=SimpleNamespace(id=user_id)),
    )


@pytest.mark.asyncio
async def test_handle_like_publishes_interaction_event() -> None:
    query = _query_with_user(101)
    resolved = ResolvedCallback(handler_id="handle_like", path_params={"profile_id": "202"})
    publisher = AsyncMock()
    get_profile = AsyncMock()
    get_profile.execute.return_value = SimpleNamespace(name="Test User")
    profile_service = AsyncMock()
    profile_service.get_profile_by_id.return_value = None
    ranking_service = AsyncMock()
    ranking_service.get_next_candidate.return_value = (202, 5)

    await handle_like(query, resolved, publisher, get_profile, profile_service, ranking_service)

    assert publisher.publish.await_count == 2
    published = [call.args for call in publisher.publish.await_args_list]
    assert ("interaction.like", b'{"liker_telegram_id": 101, "liked_telegram_id": 202, "status": "liked"}') in published
    assert ("ranking.interaction.like", b'{"liker_telegram_id": 101, "liked_telegram_id": 202}') in published
    query.answer.assert_awaited_once_with("❤️")
    query.message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_skip_publishes_interaction_event() -> None:
    query = _query_with_user(303)
    resolved = ResolvedCallback(handler_id="handle_skip", path_params={"profile_id": "404"})
    publisher = AsyncMock()
    cache = AsyncMock()
    get_profile = AsyncMock()
    get_profile.execute.return_value = SimpleNamespace(name="Test User")
    profile_service = AsyncMock()
    profile_service.get_profile_by_id.return_value = None
    ranking_service = AsyncMock()
    ranking_service.get_next_candidate.return_value = (404, 3)

    await handle_skip(query, resolved, publisher, cache, get_profile, profile_service, ranking_service)

    assert publisher.publish.await_count == 2
    cache.set.assert_awaited_once()
    published = [call.args for call in publisher.publish.await_args_list]
    assert ("interaction.skip", b'{"actor_telegram_id": 303, "target_telegram_id": 404}') in published
    assert ("ranking.interaction.skip", b'{"actor_telegram_id": 303, "target_telegram_id": 404}') in published
    query.answer.assert_awaited_once_with("👎")
    query.message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_undo_restores_last_skipped_profile() -> None:
    query = _query_with_user(505)
    resolved = ResolvedCallback(handler_id="handle_undo", path_params={})
    cache = AsyncMock()
    cache.get.return_value = 606
    profile_service = AsyncMock()
    profile_service.get_profile_by_id.return_value = SimpleNamespace(
        profile_id=606,
        telegram_id=606,
        name="Restored User",
        age=27,
        city="Moscow",
        bio="Bio",
        gender=SimpleNamespace(value="female"),
        photos=[],
    )

    await handle_undo(query, resolved, cache, profile_service)

    cache.delete.assert_awaited_once_with("last_skip:505")
    profile_service.get_profile_by_id.assert_awaited_once_with(606)
    query.answer.assert_awaited_once_with("Анкета возвращена")
    query.bot.send_message.assert_awaited_once()
