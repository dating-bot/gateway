from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message


def register_handlers(router: Router) -> None:
    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:  # pyright: ignore[reportUnusedFunction]
        _ = await message.answer("Gateway OK")
