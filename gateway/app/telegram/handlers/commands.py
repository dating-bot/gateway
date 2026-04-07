"""Обработчики команд /start, /menu, /cancel."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from dishka.integrations.aiogram import FromDishka

from gateway.app.telegram.fsm.states import RegistrationState
from gateway.usecases.profile.get_profile import GetProfile

commands_router = Router(name="commands")

_MAIN_MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Мой профиль", callback_data="menu:profile:view"),
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="menu:profile:edit"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
            InlineKeyboardButton(text="💎 Подписка", callback_data="billing:subscribe"),
        ],
    ]
)


@commands_router.message(Command("start"))
async def handle_start(
    message: Message,
    state: FSMContext,
    get_profile: FromDishka[GetProfile],
) -> None:
    telegram_id = message.from_user.id if message.from_user else 0
    profile = await get_profile.execute(telegram_id)

    if profile is not None:
        await message.answer(
            f"С возвращением, {profile.name}! 👋",
            reply_markup=_MAIN_MENU_KB,
        )
        return

    await state.set_state(RegistrationState.enter_name)
    await message.answer("Привет! 👋 Давай создадим твой профиль.\n\nКак тебя зовут?")


@commands_router.message(Command("menu"))
async def handle_menu(
    message: Message,
    get_profile: FromDishka[GetProfile],
) -> None:
    telegram_id = message.from_user.id if message.from_user else 0
    profile = await get_profile.execute(telegram_id)

    if profile is None:
        await message.answer("Сначала создай профиль через /start")
        return

    await message.answer("Главное меню:", reply_markup=_MAIN_MENU_KB)


@commands_router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer("Нечего отменять.")
        return
    await state.clear()
    await message.answer("Действие отменено.")
