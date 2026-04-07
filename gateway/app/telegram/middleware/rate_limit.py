"""RateLimitMiddleware — защита от flood атак.

Порядок: ПЕРВЫЙ middleware в цепочке.
Счётчик: rl:user:{uid}, инкремент в Valkey. При count > limit → drop update.
"""

from collections.abc import Awaitable, Callable
from typing import Any, final

import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from gateway.infra.metrics import rate_limit_exceeded_total
from gateway.pkg.telegram.update_user import user_id_from_update
from gateway.protocols.coordination import CoordinationProtocol

log = structlog.stdlib.get_logger("gateway.middleware.RateLimitMiddleware")

_WINDOW_SEC = 60


@final
class RateLimitMiddleware(BaseMiddleware):
    """Ограничивает макс. rate_limit_per_minute действий в минуту на пользователя."""

    def __init__(self, *, coordination: CoordinationProtocol, limit: int) -> None:
        self._coordination = coordination
        self._limit = limit

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        update: Update | None = data.get("event_update")
        if update is None:
            return await handler(event, data)

        uid = user_id_from_update(update)
        if uid is None:
            return await handler(event, data)

        key = f"rl:user:{uid}"
        count = await self._coordination.incr_with_expire(key, _WINDOW_SEC)

        if count > self._limit:
            rate_limit_exceeded_total.inc()
            log.info("rate limit exceeded, dropping update", user_id=uid, count=count)
            # Ответить пользователю если это callback или message
            if update.callback_query:
                await update.callback_query.answer("⏳ Слишком много запросов, подожди немного")
            elif update.message:
                await update.message.answer("⏳ Слишком много запросов, подожди немного")
            return None

        return await handler(event, data)
