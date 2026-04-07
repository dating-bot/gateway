"""Callback dispatcher — маршрутизирует по handler_id из ResolvedCallback.

Все callback_query уже прошли через CallbackRadixAclMiddleware.
Этот роутер — единственная точка входа для callback_query.
"""

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import Router
from aiogram.types import CallbackQuery
from dishka.integrations.aiogram import FromDishka

from gateway.app.telegram.handlers.profile_view import handle_profile_edit, handle_profile_view
from gateway.app.telegram.handlers.stubs import handle_stub
from gateway.app.telegram.middleware.callback_dispatch import RESOLVED_CALLBACK_KEY
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.usecases.profile.get_profile import GetProfile
from gateway.usecases.profile.upload_photo import UploadPhoto

log = structlog.stdlib.get_logger("gateway.handlers.callback_reply")

callback_router = Router(name="callback_reply")

# Таблица handler_id → функция
# Тип: (query, resolved, **dishka_deps) -> None
_HANDLER_MAP: dict[str, Callable[..., Awaitable[Any]]] = {
    "handle_profile_view": handle_profile_view,
    "handle_profile_edit": handle_profile_edit,
    # стабы — все остальные
}

_STUB_HANDLERS = {
    "handle_like",
    "handle_skip",
    "handle_undo",
    "handle_super_like",
    "handle_settings",
    "handle_subscribe",
    "handle_boost",
    "handle_cancel_sub",
    "handle_ban",
    "handle_unban",
}


@callback_router.callback_query()
async def dispatch_callback(
    query: CallbackQuery,
    get_profile: FromDishka[GetProfile],
    upload_photo: FromDishka[UploadPhoto],
    **data: Any,
) -> None:
    resolved: ResolvedCallback | None = data.get(RESOLVED_CALLBACK_KEY)
    if resolved is None:
        # middleware не положил resolved — значит update не прошёл ACL (уже обработан)
        return

    handler_id = resolved.handler_id
    log.debug("dispatching callback", handler_id=handler_id, path_params=resolved.path_params)

    if handler_id == "handle_profile_view":
        await handle_profile_view(query, resolved, get_profile)
    elif handler_id == "handle_profile_edit":
        await handle_profile_edit(query, resolved, get_profile)
    elif handler_id in _STUB_HANDLERS:
        await handle_stub(query, resolved)
    else:
        log.warning("unknown handler_id in callback dispatch", handler_id=handler_id)
        await query.answer("❓ Неизвестная команда")
