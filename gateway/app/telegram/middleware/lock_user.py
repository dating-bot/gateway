from collections.abc import Awaitable, Callable
from typing import Any, final

import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from gateway.pkg.telegram.update_user import user_id_from_update
from gateway.protocols.coordination import CoordinationProtocol

log = structlog.stdlib.get_logger("gateway.middleware.LockUserMiddleware")

_LOCK_VALUE = "1"


@final
class LockUserMiddleware(BaseMiddleware):
    def __init__(self, *, coordination: CoordinationProtocol, lock_ttl_sec: int = 5) -> None:
        self._coordination = coordination
        self._lock_ttl_sec = lock_ttl_sec

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

        lock_key = f"lock:user:{uid}"
        acquired = await self._coordination.set_nx(lock_key, _LOCK_VALUE, self._lock_ttl_sec)
        if not acquired:
            log.debug("lock not acquired, dropping update", user_id=uid)
            if event.callback_query is not None:
                _ = await event.callback_query.answer(
                    "⏳ Подожди, предыдущий запрос ещё обрабатывается.",
                )
            return None

        try:
            return await handler(event, data)
        finally:
            await self._coordination.delete(lock_key)
