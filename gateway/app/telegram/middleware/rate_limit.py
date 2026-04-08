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
        if not isinstance(event, Update):
            return await handler(event, data)

        uid = user_id_from_update(event)
        if uid is None:
            return await handler(event, data)

        key = f"rl:user:{uid}"
        count = await self._coordination.incr_with_expire(key, _WINDOW_SEC)

        if count > self._limit:
            rate_limit_exceeded_total.inc()
            log.info("rate limit exceeded, dropping update", user_id=uid, count=count)
            # Ответить пользователю если это callback или message
            if event.callback_query:
                await event.callback_query.answer("⏳ Слишком много запросов, подожди немного")
            elif event.message:
                await event.message.answer("⏳ Слишком много запросов, подожди немного")
            return None

        return await handler(event, data)
