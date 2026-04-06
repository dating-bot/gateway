from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from dishka.integrations.aiogram import FromDishka

from gateway.usecases.callback_routing.resolve_route import ResolveCallbackRouteUsecase


def register_handlers(router: Router) -> None:
    @router.message(CommandStart())
    async def cmd_start(  # pyright: ignore[reportUnusedFunction]
        message: Message,
        resolve_route: FromDishka[ResolveCallbackRouteUsecase],
    ) -> None:
        _ = resolve_route.execute("__ping__")
        _ = await message.answer("Gateway OK")
