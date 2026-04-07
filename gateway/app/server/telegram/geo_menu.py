"""Команда /menu и сохранение геолокации (SetGeo)."""

from typing import Annotated

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from dishka import FromDishka

from gateway.app.server.telegram.registration_fsm import PhotoPrompt
from gateway.usecases.profile.errors import ProfileNotFoundForMutationError, ProfileServiceTransportError
from gateway.usecases.profile.get_profile import GetProfile
from gateway.usecases.profile.set_geo import SetGeo

log = structlog.stdlib.get_logger("gateway.app.server.telegram.geo_menu")


def _menu_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 Профиль", callback_data="menu:profile:view"),
                InlineKeyboardButton(text="✏️ Редактировать", callback_data="menu:profile:edit"),
            ],
            [
                InlineKeyboardButton(text="❤️ Лайк", callback_data="like"),
                InlineKeyboardButton(text="⏭ Пропуск", callback_data="skip"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
                InlineKeyboardButton(text="💎 Подписка", callback_data="billing:subscribe"),
            ],
        ],
    )


def _geo_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отправить гео", request_location=True)]],
        resize_keyboard=True,
    )


def register_geo_and_menu(router: Router) -> None:
    @router.message(Command("menu"))
    async def cmd_menu(  # pyright: ignore[reportUnusedFunction]
        message: Message,
    ) -> None:
        text = (
            "Меню dating bot:\n"
            "— кнопки ниже (callback);\n"
            "— гео: «Отправить гео» или скрепка → Location (нужен профиль);\n"
            "— регистрация: /start, отмена: /cancel."
        )
        _ = await message.answer(text, reply_markup=_menu_inline())
        _ = await message.answer("Геолокация (для будущего «рядом»):", reply_markup=_geo_reply_keyboard())

    @router.message(F.location)
    async def on_location(  # pyright: ignore[reportUnusedFunction]
        message: Message,
        state: FSMContext,
        get_profile: Annotated[GetProfile, FromDishka()],
        set_geo: Annotated[SetGeo, FromDishka()],
    ) -> None:
        if message.from_user is None or message.location is None:
            return
        current = await state.get_state()
        if current is not None and current != PhotoPrompt.waiting.state:
            _ = await message.answer("Сначала завершите текущий шаг (/cancel или /skip_photo).")
            return
        response = await get_profile.execute(GetProfile.Request(telegram_id=message.from_user.id))
        if response.profile is None:
            _ = await message.answer("Сначала создай профиль: /start")
            return
        try:
            await set_geo.execute(
                SetGeo.Request(
                    telegram_id=message.from_user.id,
                    latitude=message.location.latitude,
                    longitude=message.location.longitude,
                ),
            )
        except ProfileNotFoundForMutationError:
            _ = await message.answer("Профиль не найден. /start")
            return
        except ProfileServiceTransportError:
            log.exception("set_geo failed")
            _ = await message.answer("Не удалось сохранить гео. Попробуй позже.")
            return
        reply = "Геолокация сохранена."
        if await state.get_state() == PhotoPrompt.waiting.state:
            reply += " Пришли фото или /skip_photo."
        _ = await message.answer(reply)
