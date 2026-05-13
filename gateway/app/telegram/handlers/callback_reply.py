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

from gateway.app.telegram.handlers.commands import (
    handle_menu_browse,
    handle_menu_dating_status,
    handle_menu_geo_request,
    handle_menu_main,
    handle_menu_more,
)
from gateway.app.telegram.handlers.like_skip import handle_like, handle_skip, handle_super_like, handle_undo
from gateway.app.telegram.handlers.payments import (
    handle_subscribe,
    handle_subscribe_provider,
    handle_subscribe_stars,
)
from gateway.app.telegram.handlers.preferences import (
    handle_settings,
    handle_settings_premium,
    handle_settings_profile_pause,
    handle_settings_profile_resume,
    handle_settings_search,
    handle_settings_search_age,
    handle_settings_search_distance,
    handle_settings_search_gender,
    handle_settings_support,
    handle_settings_terms,
)
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
from gateway.infra.telegram import TelegramConfig
from gateway.protocols.cache import CacheProtocol
from gateway.protocols.events import EventPublisherProtocol
from gateway.protocols.profile import ProfileServiceProtocol
from gateway.protocols.ranking_service import RankingServiceProtocol
from gateway.usecases.dating.check_status import CheckDatingStatus
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
    "handle_boost",
    "handle_cancel_sub",
    "handle_ban",
    "handle_unban",
}


@callback_router.callback_query()
async def dispatch_callback(  # noqa: C901, PLR0912, PLR0913, PLR0915
    query: CallbackQuery,
    get_profile: FromDishka[GetProfile],
    delete_photo: FromDishka[DeletePhoto],
    profile_service: FromDishka[ProfileServiceProtocol],
    event_publisher: FromDishka[EventPublisherProtocol],
    ranking_service: FromDishka[RankingServiceProtocol],
    check_dating_status: FromDishka[CheckDatingStatus],
    cache: FromDishka[CacheProtocol],
    telegram_config: FromDishka[TelegramConfig],
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
    elif handler_id == "handle_menu_browse":
        await handle_menu_browse(query, resolved, get_profile, profile_service, ranking_service, cache)
    elif handler_id == "handle_menu_dating_status":
        await handle_menu_dating_status(query, resolved, get_profile, check_dating_status)
    elif handler_id == "handle_menu_more":
        await handle_menu_more(query, resolved, get_profile)
    elif handler_id == "handle_menu_main":
        await handle_menu_main(query, resolved, get_profile)
    elif handler_id == "handle_menu_geo_request":
        await handle_menu_geo_request(query, resolved, get_profile)
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
        await handle_like(
            query,
            resolved,
            event_publisher,
            cache,
            get_profile,
            profile_service,
            ranking_service,
            telegram_config,
        )
    elif handler_id == "handle_super_like":
        await handle_super_like(
            query,
            resolved,
            event_publisher,
            cache,
            get_profile,
            profile_service,
            ranking_service,
            telegram_config,
        )
    elif handler_id == "handle_skip":
        await handle_skip(query, resolved, event_publisher, cache, get_profile, profile_service, ranking_service)
    elif handler_id == "handle_undo":
        await handle_undo(query, resolved, event_publisher, cache, profile_service, telegram_config)
    elif handler_id == "handle_subscribe":
        await handle_subscribe(query, resolved, get_profile, telegram_config)
    elif handler_id == "handle_subscribe_stars":
        await handle_subscribe_stars(query, resolved, get_profile, telegram_config)
    elif handler_id == "handle_subscribe_provider":
        await handle_subscribe_provider(query, resolved, get_profile, telegram_config)
    elif handler_id == "handle_settings":
        await handle_settings(query, resolved, get_profile, profile_service, cache)
    elif handler_id == "handle_settings_search":
        await handle_settings_search(query, resolved, profile_service)
    elif handler_id == "handle_settings_search_gender":
        await handle_settings_search_gender(query, resolved, profile_service)
    elif handler_id == "handle_settings_search_age":
        await handle_settings_search_age(query, resolved, profile_service)
    elif handler_id == "handle_settings_search_distance":
        await handle_settings_search_distance(query, resolved, profile_service)
    elif handler_id == "handle_settings_profile_pause":
        await handle_settings_profile_pause(query, resolved, get_profile, profile_service, cache)
    elif handler_id == "handle_settings_profile_resume":
        await handle_settings_profile_resume(query, resolved, get_profile, profile_service, cache)
    elif handler_id == "handle_settings_premium":
        await handle_settings_premium(query, resolved, get_profile, telegram_config)
    elif handler_id == "handle_settings_support":
        await handle_settings_support(query, resolved)
    elif handler_id == "handle_settings_terms":
        await handle_settings_terms(query, resolved)
    elif handler_id in _STUB_HANDLERS:
        await handle_stub(query, resolved)
    else:
        log.warning("unknown handler_id in callback dispatch", handler_id=handler_id)
        _ = await query.answer("❓ Неизвестная команда")
