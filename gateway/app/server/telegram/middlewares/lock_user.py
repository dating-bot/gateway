from collections.abc import Awaitable, Callable
from typing import final, override

import structlog
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject, Update

from gateway.infra.valkey import ValkeyConfig
from gateway.pkg.telegram.update_user import user_id_from_update
from gateway.protocols.coordination import CoordinationProtocol

log = structlog.stdlib.get_logger("gateway.app.server.telegram.middlewares.lock_user_middleware")


@final
class LockUserMiddleware(BaseMiddleware):
    _valkey: CoordinationProtocol
    _ttl: int

    def __init__(self, valkey: CoordinationProtocol, cfg: ValkeyConfig) -> None:
        self._valkey = valkey
        self._ttl = cfg.user_lock_ttl_sec

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
        lock_key = f"lock:user:{uid}"
        got = await self._valkey.set_nx(lock_key, "1", self._ttl)
        if not got:
            log.warning("user_lock_busy", user_id=uid)
            return None
        try:
            return await handler(event, data)
        finally:
            await self._valkey.delete(lock_key)
