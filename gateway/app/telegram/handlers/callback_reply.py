"""Callback dispatcher — маршрутизирует по handler_id из ResolvedCallback.

Все callback_query уже прошли через CallbackRadixAclMiddleware.
Этот роутер — единственная точка входа для callback_query.
"""

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from dishka.integrations.aiogram import FromDishka

from gateway.app.telegram.handlers.like_skip import handle_like, handle_skip
from gateway.app.telegram.handlers.profile_photos import (
    handle_photos_add,
    handle_photos_delete,
    handle_profile_photos_menu,
)
from gateway.app.telegram.handlers.profile_view import (
    handle_edit_field_select,
    handle_profile_edit,
    handle_profile_view,
)
from gateway.app.telegram.handlers.stubs import handle_stub
from gateway.app.telegram.middleware.callback_dispatch import RESOLVED_CALLBACK_KEY
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.protocols.match_service import MatchServiceProtocol
from gateway.protocols.profile import ProfileServiceProtocol
from gateway.usecases.profile.delete_photo import DeletePhoto
from gateway.usecases.profile.get_profile import GetProfile

log = structlog.stdlib.get_logger("gateway.handlers.callback_reply")

callback_router = Router(name="callback_reply")

# Таблица handler_id → функция
# Тип: (query, resolved, **dishka_deps) -> None
_HANDLER_MAP: dict[str, Callable[..., Awaitable[Any]]] = {
    "handle_profile_view": handle_profile_view,
    "handle_profile_edit": handle_profile_edit,
    "handle_like": handle_like,
    "handle_skip": handle_skip,
    # стабы — все остальные
}

_STUB_HANDLERS = {
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
async def dispatch_callback(  # noqa: PLR0913
    query: CallbackQuery,
    get_profile: FromDishka[GetProfile],
    delete_photo: FromDishka[DeletePhoto],
    profile_service: FromDishka[ProfileServiceProtocol],
    match_service: FromDishka[MatchServiceProtocol],
    state: FSMContext,
    resolved_callback: ResolvedCallback | None = None,
    **data: Any,
) -> None:
    resolved: ResolvedCallback | None = resolved_callback or data.get(RESOLVED_CALLBACK_KEY)
    if resolved is None:
        # middleware не положил resolved — значит update не прошёл ACL (уже обработан)
        return

    handler_id = resolved.handler_id
    log.debug("dispatching callback", handler_id=handler_id, path_params=resolved.path_params)

    if handler_id == "handle_profile_view":
        await handle_profile_view(query, resolved, get_profile, profile_service)
    elif handler_id == "handle_profile_edit":
        await handle_profile_edit(query, resolved, get_profile)
    elif handler_id == "handle_profile_photos_menu":
        await handle_profile_photos_menu(query, resolved, get_profile)
    elif handler_id == "handle_photos_add":
        await handle_photos_add(query, resolved, state)
    elif handler_id == "handle_photos_delete":
        await handle_photos_delete(query, resolved, delete_photo, get_profile)
    elif handler_id == "handle_edit_field_select":
        await handle_edit_field_select(query, resolved, state, get_profile)
    elif handler_id == "handle_like":
        await handle_like(query, resolved, match_service)
    elif handler_id == "handle_skip":
        await handle_skip(query, resolved, match_service)
    elif handler_id in _STUB_HANDLERS:
        await handle_stub(query, resolved)
    else:
        log.warning("unknown handler_id in callback dispatch", handler_id=handler_id)
        _ = await query.answer("❓ Неизвестная команда")
