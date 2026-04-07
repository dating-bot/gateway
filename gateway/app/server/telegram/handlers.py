from typing import cast

import structlog
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from gateway.app.server.telegram.callback_replies import CALLBACK_STUB_ANSWER
from gateway.app.server.telegram.middlewares.callback_dispatch import RESOLVED_CALLBACK_KEY
from gateway.domain.resolved_callback import ResolvedCallback

log = structlog.stdlib.get_logger("gateway.app.server.telegram.handlers")


def register_handlers(router: Router) -> None:
    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:  # pyright: ignore[reportUnusedFunction]
        _ = await message.answer("Gateway OK")

    @router.callback_query()
    async def dispatch_callback(  # pyright: ignore[reportUnusedFunction]
        query: CallbackQuery,
        **data: object,
    ) -> None:
        resolved = cast("ResolvedCallback | None", data.get(RESOLVED_CALLBACK_KEY))
        if resolved is None:
            _ = await query.answer()
            return

        # Per-request trace at DEBUG; at INFO this line is skipped (better RPS under load).
        log.debug(
            "dispatching callback",
            handler_id=resolved.handler_id,
            user_id=query.from_user.id if query.from_user else None,
        )

        text = CALLBACK_STUB_ANSWER.get(resolved.handler_id)
        if text is None:
            log.warning("unknown handler_id", handler_id=resolved.handler_id)
            _ = await query.answer()
            return

        _ = await query.answer(text)
