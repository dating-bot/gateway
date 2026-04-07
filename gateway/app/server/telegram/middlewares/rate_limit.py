from collections.abc import Awaitable, Callable
from typing import final, override

import structlog
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject, Update

from gateway.infra.valkey import ValkeyConfig
from gateway.pkg.telegram.update_user import user_id_from_update
from gateway.protocols.coordination import CoordinationProtocol

log = structlog.stdlib.get_logger("gateway.app.server.telegram.middlewares.rate_limit_middleware")


@final
class RateLimitMiddleware(BaseMiddleware):
    _valkey: CoordinationProtocol
    _limit: int
    _window: int

    def __init__(self, valkey: CoordinationProtocol, cfg: ValkeyConfig) -> None:
        self._valkey = valkey
        self._limit = cfg.rate_limit_per_minute
        self._window = cfg.rate_limit_window_seconds

    @override
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, object]], Awaitable[object]],
        event: TelegramObject,
        data: dict[str, object],
    ) -> object:
        if not isinstance(event, Update):
            return await handler(event, data)
        uid = user_id_from_update(event)
        if uid is None:
            return await handler(event, data)
        count = await self._valkey.incr_with_expire(f"rl:user:{uid}", self._window)
        if count > self._limit:
            log.warning("rate_limit_exceeded", user_id=uid, count=count)
            return None
        return await handler(event, data)
