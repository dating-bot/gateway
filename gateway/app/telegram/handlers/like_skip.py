import structlog
from aiogram.types import CallbackQuery

from gateway.app.telegram.handlers.stubs import _STUB_ANSWERS
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.protocols.cache import CacheProtocol
from gateway.protocols.match_service import MatchServiceProtocol

log = structlog.stdlib.get_logger("gateway.handlers.like_skip")


async def handle_like(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    match_service: MatchServiceProtocol,
) -> None:
    liker_id = query.from_user.id
    liked_id = int(resolved.path_params["profile_id"])

    try:
        matched, match_id = await match_service.handle_like(liker_id, liked_id)
        if matched:
            answer = "❤️ It's a match! 🎉"
            log.info("match created via callback", liker_id=liker_id, liked_id=liked_id, match_id=match_id)
        else:
            answer = _STUB_ANSWERS.get("handle_like", "❤️")
            log.debug("like processed", liker_id=liker_id, liked_id=liked_id)
    except Exception:
        log.exception("handle_like failed", liker_id=liker_id, liked_id=liked_id)
        answer = "❌ Ошибка"

    _ = await query.answer(answer)


async def handle_skip(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    match_service: MatchServiceProtocol,
) -> None:
    actor_id = query.from_user.id
    target_id = int(resolved.path_params["profile_id"])

    try:
        await match_service.handle_skip(actor_id, target_id)
        answer = _STUB_ANSWERS.get("handle_skip", "👎")
        log.debug("skip processed", actor_id=actor_id, target_id=target_id)
    except Exception:
        log.exception("handle_skip failed", actor_id=actor_id, target_id=target_id)
        answer = "❌ Ошибка"

    _ = await query.answer(answer)


async def handle_undo(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    cache: CacheProtocol,
) -> None:
    user_id = query.from_user.id
    key = f"last_skip:{user_id}"

    try:
        last_skipped = await cache.get(key, unmarshal_as=int)
        if last_skipped is None:
            answer = "Время вышло (30 мин) 🔄"
        else:
            await cache.delete(key)
            answer = f"Вернулись к профилю #{last_skipped}"
            log.info("undo successful", user_id=user_id, restored_profile_id=last_skipped)
    except Exception:
        log.exception("handle_undo failed", user_id=user_id)
        answer = "❌ Ошибка"

    _ = await query.answer(answer)
