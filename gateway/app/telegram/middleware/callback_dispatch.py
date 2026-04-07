"""CallbackRadixAclMiddleware — маршрутизация callback_data + ACL.

Порядок: ТРЕТИЙ middleware (после Lock).
Только для callback_query updates.
Резолвит callback_data → ResolvedCallback, проверяет ACL, прокидывает в data.
"""

from collections.abc import Awaitable, Callable
from typing import Any, final

import structlog
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject, Update

from gateway.protocols.acl import AclCheckerProtocol
from gateway.usecases.callback_routing.resolve import ResolveCallbackRoute

log = structlog.stdlib.get_logger("gateway.middleware.CallbackRadixAclMiddleware")

RESOLVED_CALLBACK_KEY = "resolved_callback"


@final
class CallbackRadixAclMiddleware(BaseMiddleware):
    """Для callback_query: разбирает callback_data через radix tree, проверяет ACL.

    Если маршрут не найден или ACL запрещает → отвечает пользователю и останавливает обработку.
    Иначе кладёт ResolvedCallback в data[RESOLVED_CALLBACK_KEY].
    """

    def __init__(self, *, resolve_usecase: ResolveCallbackRoute, acl: AclCheckerProtocol) -> None:
        self._resolve = resolve_usecase
        self._acl = acl

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        update: Update | None = data.get("event_update")
        if update is None or update.callback_query is None:
            return await handler(event, data)

        query: CallbackQuery = update.callback_query
        callback_data = query.data or ""
        user_id = query.from_user.id

        resolved = self._resolve.execute(callback_data)
        if resolved is None:
            log.debug("unmatched callback_data", callback_data=callback_data, user_id=user_id)
            await query.answer("❓ Неизвестная команда")
            return None

        allowed = await self._acl.check(user_id, resolved.requires)
        if not allowed:
            log.info("acl denied", user_id=user_id, handler_id=resolved.handler_id)
            await query.answer("🚫 Нет доступа")
            return None

        data[RESOLVED_CALLBACK_KEY] = resolved
        return await handler(event, data)
