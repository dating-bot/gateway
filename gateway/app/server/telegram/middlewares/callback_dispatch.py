from collections.abc import Awaitable, Callable
from typing import final, override

import structlog
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject, Update

from gateway.infra.metrics import radix_tree_unmatched_total
from gateway.protocols.acl import AclChecker
from gateway.usecases.callback_routing.resolve_route import ResolveCallbackRoute

log = structlog.stdlib.get_logger("gateway.app.server.telegram.middlewares.callback_dispatch")

RESOLVED_CALLBACK_KEY = "resolved_callback"


@final
class CallbackRadixAclMiddleware(BaseMiddleware):
    """Resolve callback_data via radix; stub ACL; increment unmatched metric."""

    _resolve_route: ResolveCallbackRoute
    _acl: AclChecker

    def __init__(self, resolve_route: ResolveCallbackRoute, acl: AclChecker) -> None:
        self._resolve_route = resolve_route
        self._acl = acl

    @override
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, object]], Awaitable[object]],
        event: TelegramObject,
        data: dict[str, object],
    ) -> object:
        if not isinstance(event, Update):
            return await handler(event, data)
        cq = event.callback_query
        if cq is None or cq.data is None:
            return await handler(event, data)
        resolved = self._resolve_route.execute(ResolveCallbackRoute.Request(callback_data=cq.data)).resolved
        if resolved is None:
            radix_tree_unmatched_total.inc()
            return await handler(event, data)
        allowed = await self._acl.check(cq.from_user.id, resolved.requires)
        if not allowed:
            log.warning("acl_denied", user_id=cq.from_user.id, handler_id=resolved.handler_id)
            return None
        data[RESOLVED_CALLBACK_KEY] = resolved
        return await handler(event, data)
