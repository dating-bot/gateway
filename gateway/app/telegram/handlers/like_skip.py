import json
import time
from datetime import UTC, datetime, timedelta

import structlog
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from gateway.app.telegram.handlers.commands import _send_candidate_profile, _send_next_candidate
from gateway.app.telegram.handlers.stubs import _STUB_ANSWERS
from gateway.domain.profile import Profile, SubscriptionTier
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.infra.telegram import TelegramConfig
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
RANKING_INTERACTION_UNDO_SKIP_QUEUE = "ranking.interaction.undo_skip"
UNDO_TTL = timedelta(minutes=30)
SEEN_TTL = timedelta(days=30)
_ACTION_LIKE = "like"
_ACTION_SUPER_LIKE = "super_like"
_ACTION_UNDO = "undo"

_UPGRADE_KB = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="💎 Оформить Premium", callback_data="billing:subscribe")]]
)


def _is_premium_active(profile: Profile | None) -> bool:
    if profile is None or profile.subscription_tier != SubscriptionTier.PREMIUM:
        return False
    expires_at = profile.subscription_expires_at_seconds or 0
    return expires_at > int(time.time())


def _seconds_until_next_utc_day() -> int:
    now = datetime.now(tz=UTC)
    tomorrow = datetime(now.year, now.month, now.day, tzinfo=UTC) + timedelta(days=1)
    return max(1, int((tomorrow - now).total_seconds()))


def _limit_key(*, action: str, user_id: int) -> str:
    day = datetime.now(tz=UTC).date().isoformat()
    return f"limit:{action}:{user_id}:{day}"


async def _consume_daily_limit(
    *,
    cache: CacheProtocol,
    action: str,
    user_id: int,
    limit: int | None,
) -> bool:
    if limit is None:
        return True
    key = _limit_key(action=action, user_id=user_id)
    used = await cache.get(key, unmarshal_as=int) or 0
    if used >= limit:
        return False
    await cache.set(key, used + 1, ttl=timedelta(seconds=_seconds_until_next_utc_day()))
    return True


def _free_limit(*, action: str, config: TelegramConfig) -> int:
    if action == _ACTION_LIKE:
        return config.free_like_daily_limit
    if action == _ACTION_SUPER_LIKE:
        return config.free_super_like_daily_limit
    if action == _ACTION_UNDO:
        return config.free_undo_daily_limit
    msg = f"unknown action for limits: {action}"
    raise ValueError(msg)


async def _reply_limit_exceeded(query: CallbackQuery, *, action: str) -> None:
    if action == _ACTION_LIKE:
        reason = "Лимит лайков на сегодня исчерпан."
    elif action == _ACTION_SUPER_LIKE:
        reason = "Лимит Super Like на сегодня исчерпан."
    else:
        reason = "Лимит Undo на сегодня исчерпан."
    _ = await query.answer("Лимит исчерпан")
    if query.message is not None:
        _ = await query.message.answer(
            f"{reason}\nС Premium доступно больше возможностей.",
            reply_markup=_UPGRADE_KB,
        )


async def handle_super_like(  # noqa: PLR0913
    query: CallbackQuery,
    resolved: ResolvedCallback,
    events: EventPublisherProtocol,
    cache: CacheProtocol,
    get_profile: GetProfile,
    profile_service: ProfileServiceProtocol,
    ranking_service: RankingServiceProtocol,
    config: TelegramConfig,
) -> None:
    liker_id = query.from_user.id
    liked_id = int(resolved.path_params["profile_id"])

    profile = await get_profile.execute(liker_id)
    is_premium = _is_premium_active(profile)
    limit = None if is_premium else _free_limit(action=_ACTION_SUPER_LIKE, config=config)
    allowed = await _consume_daily_limit(cache=cache, action=_ACTION_SUPER_LIKE, user_id=liker_id, limit=limit)
    if not allowed:
        await _reply_limit_exceeded(query, action=_ACTION_SUPER_LIKE)
        return

    try:
        await events.publish(
            INTERACTION_LIKE_QUEUE,
            json.dumps({
                "liker_telegram_id": liker_id,
                "liked_telegram_id": liked_id,
                "status": "superliked",
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
            log.exception("ranking super like event publish failed", liker_id=liker_id, liked_id=liked_id)
        answer = "⭐"
        log.info("super like event published", liker_id=liker_id, liked_id=liked_id, routing_key=INTERACTION_LIKE_QUEUE)
    except Exception:
        log.exception("handle_super_like publish failed", liker_id=liker_id, liked_id=liked_id)
        answer = "❌ Ошибка"
        _ = await query.answer(answer)
        return

    _ = await query.answer(answer)
    if query.message is None:
        log.warning("super like callback has no message", liker_id=liker_id, liked_id=liked_id)
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


async def handle_like(  # noqa: PLR0913
    query: CallbackQuery,
    resolved: ResolvedCallback,
    events: EventPublisherProtocol,
    cache: CacheProtocol,
    get_profile: GetProfile,
    profile_service: ProfileServiceProtocol,
    ranking_service: RankingServiceProtocol,
    config: TelegramConfig,
) -> None:
    liker_id = query.from_user.id
    liked_id = int(resolved.path_params["profile_id"])
    profile = await get_profile.execute(liker_id)
    is_premium = _is_premium_active(profile)
    limit = None if is_premium else _free_limit(action=_ACTION_LIKE, config=config)
    allowed = await _consume_daily_limit(cache=cache, action=_ACTION_LIKE, user_id=liker_id, limit=limit)
    if not allowed:
        await _reply_limit_exceeded(query, action=_ACTION_LIKE)
        return

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


async def handle_undo(  # noqa: PLR0913
    query: CallbackQuery,
    resolved: ResolvedCallback,
    events: EventPublisherProtocol,
    cache: CacheProtocol,
    profile_service: ProfileServiceProtocol,
    config: TelegramConfig,
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
            profile = await profile_service.get_profile(user_id)
            is_premium = _is_premium_active(profile)
            limit = None if is_premium else _free_limit(action=_ACTION_UNDO, config=config)
            allowed = await _consume_daily_limit(cache=cache, action=_ACTION_UNDO, user_id=user_id, limit=limit)
            if not allowed:
                await _reply_limit_exceeded(query, action=_ACTION_UNDO)
                return
            await cache.delete(key)
            await cache.delete(action_key)
            await cache.delete(f"seen:{user_id}:{last_skipped_telegram_id}")
            try:
                await events.publish(
                    RANKING_INTERACTION_UNDO_SKIP_QUEUE,
                    json.dumps({
                        "actor_telegram_id": user_id,
                        "target_telegram_id": last_skipped_telegram_id,
                    }).encode(),
                )
            except Exception:
                log.exception(
                    "ranking undo skip event publish failed",
                    user_id=user_id,
                    restored_telegram_id=last_skipped_telegram_id,
                )
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
