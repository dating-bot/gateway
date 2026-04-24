import json
from datetime import timedelta

import structlog
from aiogram.types import CallbackQuery

from gateway.app.telegram.handlers.commands import _send_candidate_profile, _send_next_candidate
from gateway.app.telegram.handlers.stubs import _STUB_ANSWERS
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.protocols.cache import CacheProtocol
from gateway.protocols.events import EventPublisherProtocol
from gateway.protocols.profile import ProfileServiceProtocol
from gateway.protocols.ranking_service import RankingServiceProtocol
from gateway.usecases.profile.get_profile import GetProfile

log = structlog.stdlib.get_logger("gateway.handlers.like_skip")

INTERACTION_LIKE_QUEUE = "interaction.like"
INTERACTION_SKIP_QUEUE = "interaction.skip"
RANKING_INTERACTION_LIKE_QUEUE = "ranking.interaction.like"
RANKING_INTERACTION_SKIP_QUEUE = "ranking.interaction.skip"
UNDO_TTL = timedelta(minutes=30)
SEEN_TTL = timedelta(days=30)


async def handle_like(  # noqa: PLR0913
    query: CallbackQuery,
    resolved: ResolvedCallback,
    events: EventPublisherProtocol,
    cache: CacheProtocol,
    get_profile: GetProfile,
    profile_service: ProfileServiceProtocol,
    ranking_service: RankingServiceProtocol,
) -> None:
    liker_id = query.from_user.id
    liked_id = int(resolved.path_params["profile_id"])

    try:
        await events.publish(
            INTERACTION_LIKE_QUEUE,
            json.dumps({
                "liker_telegram_id": liker_id,
                "liked_telegram_id": liked_id,
                "status": "liked",
            }).encode(),
        )
        try:
            await events.publish(
                RANKING_INTERACTION_LIKE_QUEUE,
                json.dumps({
                    "liker_telegram_id": liker_id,
                    "liked_telegram_id": liked_id,
                }).encode(),
            )
        except Exception:
            log.exception("ranking like event publish failed", liker_id=liker_id, liked_id=liked_id)
        answer = _STUB_ANSWERS.get("handle_like", "❤️")
        log.info("like event published", liker_id=liker_id, liked_id=liked_id, routing_key=INTERACTION_LIKE_QUEUE)
    except Exception:
        log.exception("handle_like publish failed", liker_id=liker_id, liked_id=liked_id)
        answer = "❌ Ошибка"
        _ = await query.answer(answer)
        return

    _ = await query.answer(answer)
    if query.message is None:
        log.warning("like callback has no message", liker_id=liker_id, liked_id=liked_id)
        return

    await cache.set(f"last_action:{liker_id}", "like", ttl=UNDO_TTL)
    await cache.delete(f"last_skip:{liker_id}")
    await cache.set(f"seen:{liker_id}:{liked_id}", 1, ttl=SEEN_TTL)

    await _send_next_candidate(
        telegram_id=liker_id,
        message=query.message,
        get_profile=get_profile,
        profile_service=profile_service,
        ranking_service=ranking_service,
        cache=cache,
        exclude_candidate_ids={liked_id},
    )


async def handle_skip(  # noqa: PLR0913
    query: CallbackQuery,
    resolved: ResolvedCallback,
    events: EventPublisherProtocol,
    cache: CacheProtocol,
    get_profile: GetProfile,
    profile_service: ProfileServiceProtocol,
    ranking_service: RankingServiceProtocol,
) -> None:
    actor_id = query.from_user.id
    target_id = int(resolved.path_params["profile_id"])

    try:
        await events.publish(
            INTERACTION_SKIP_QUEUE,
            json.dumps({
                "actor_telegram_id": actor_id,
                "target_telegram_id": target_id,
            }).encode(),
        )
        try:
            await events.publish(
                RANKING_INTERACTION_SKIP_QUEUE,
                json.dumps({
                    "actor_telegram_id": actor_id,
                    "target_telegram_id": target_id,
                }).encode(),
            )
        except Exception:
            log.exception("ranking skip event publish failed", actor_id=actor_id, target_id=target_id)
        answer = _STUB_ANSWERS.get("handle_skip", "👎")
        log.info("skip event published", actor_id=actor_id, target_id=target_id, routing_key=INTERACTION_SKIP_QUEUE)
    except Exception:
        log.exception("handle_skip publish failed", actor_id=actor_id, target_id=target_id)
        answer = "❌ Ошибка"
        _ = await query.answer(answer)
        return

    await cache.set(f"last_skip:{actor_id}", target_id, ttl=UNDO_TTL)
    await cache.set(f"last_action:{actor_id}", "skip", ttl=UNDO_TTL)
    await cache.set(f"seen:{actor_id}:{target_id}", 1, ttl=SEEN_TTL)
    _ = await query.answer(answer)
    if query.message is None:
        log.warning("skip callback has no message", actor_id=actor_id, target_id=target_id)
        return

    await _send_next_candidate(
        telegram_id=actor_id,
        message=query.message,
        get_profile=get_profile,
        profile_service=profile_service,
        ranking_service=ranking_service,
        cache=cache,
    )


async def handle_undo(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    cache: CacheProtocol,
    profile_service: ProfileServiceProtocol,
) -> None:
    del resolved
    user_id = query.from_user.id
    key = f"last_skip:{user_id}"
    action_key = f"last_action:{user_id}"

    try:
        last_action = await cache.get(action_key, unmarshal_as=str)
        if last_action == "like":
            answer = "После лайка undo недоступен"
            _ = await query.answer(answer)
            return

        last_skipped_telegram_id = await cache.get(key, unmarshal_as=int)
        if last_skipped_telegram_id is None:
            answer = "Можно отменить только последний skip (30 мин)"
        else:
            await cache.delete(key)
            await cache.delete(action_key)
            candidate = await profile_service.get_profile(last_skipped_telegram_id)
            if candidate is None:
                answer = f"Профиль #{last_skipped_telegram_id} уже недоступен"
            elif query.message is None:
                answer = f"Вернулись к профилю #{last_skipped_telegram_id}"
            else:
                await _send_candidate_profile(
                    bot=query.bot,
                    chat_id=query.message.chat.id,
                    candidate=candidate,
                    profile_service=profile_service,
                )
                answer = "Анкета возвращена"
            log.info("undo successful", user_id=user_id, restored_telegram_id=last_skipped_telegram_id)
    except Exception:
        log.exception("handle_undo failed", user_id=user_id)
        answer = "❌ Ошибка"

    _ = await query.answer(answer)
