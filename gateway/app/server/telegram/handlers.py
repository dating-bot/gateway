from typing import Annotated

import structlog
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka

from gateway.app.server.telegram.callback_replies import CALLBACK_STUB_ANSWER
from gateway.app.server.telegram.geo_menu import register_geo_and_menu
from gateway.app.server.telegram.registration_fsm import Registration, register_registration_handlers
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.usecases.profile.get_profile import GetProfile
from gateway.usecases.profile.invalidate_profile import InvalidateProfile

log = structlog.stdlib.get_logger("gateway.app.server.telegram.handlers")


async def _begin_profile_edit(
    query: CallbackQuery,
    state: FSMContext,
    *,
    user_id: int,
    get_profile: GetProfile,
    invalidate_profile: InvalidateProfile,
) -> None:
    await invalidate_profile.execute(InvalidateProfile.Request(telegram_id=user_id))
    response = await get_profile.execute(GetProfile.Request(telegram_id=user_id))
    if response.profile is None:
        _ = await query.answer("Профиль не найден", show_alert=True)
        return
    msg = query.message
    if msg is None:
        _ = await query.answer("Сообщение устарело", show_alert=True)
        return
    await state.set_state(Registration.name)
    await state.update_data(mode="update")
    _ = await query.answer()
    _ = await msg.answer("Редактирование профиля. Введи новое имя (как в анкете):")


def register_handlers(router: Router) -> None:
    register_geo_and_menu(router)
    register_registration_handlers(router)

    @router.message(CommandStart())
    async def cmd_start(  # pyright: ignore[reportUnusedFunction]
        message: Message,
        state: FSMContext,
        get_profile: Annotated[GetProfile, FromDishka()],
    ) -> None:
        if message.from_user is None:
            _ = await message.answer("Привет!")
            return

        await state.clear()
        response = await get_profile.execute(GetProfile.Request(telegram_id=message.from_user.id))
        if response.profile is not None:
            _ = await message.answer(f"С возвращением, {response.profile.name}!")
        else:
            await state.set_state(Registration.name)
            _ = await state.update_data(mode="create")
            _ = await message.answer(
                "Добро пожаловать! Давай создадим твой профиль.\n\nКак тебя зовут?",
            )

    @router.callback_query()
    async def dispatch_callback(  # pyright: ignore[reportUnusedFunction]
        query: CallbackQuery,
        state: FSMContext,
        get_profile: Annotated[GetProfile, FromDishka()],
        invalidate_profile: Annotated[InvalidateProfile, FromDishka()],
        resolved_callback: ResolvedCallback | None = None,
    ) -> None:
        if resolved_callback is None:
            _ = await query.answer()
            return

        log.debug(
            "dispatching callback",
            handler_id=resolved_callback.handler_id,
            user_id=query.from_user.id if query.from_user else None,
        )

        user_id = query.from_user.id if query.from_user else None

        if resolved_callback.handler_id == "handle_profile_view" and user_id:
            response = await get_profile.execute(GetProfile.Request(telegram_id=user_id))
            if response.profile is not None:
                text = f"👤 {response.profile.name}, {response.profile.age} лет, {response.profile.city}"
            else:
                text = "Профиль не найден"
            _ = await query.answer(text, show_alert=True)
            return

        if resolved_callback.handler_id == "handle_profile_edit" and user_id:
            await _begin_profile_edit(
                query,
                state,
                user_id=user_id,
                get_profile=get_profile,
                invalidate_profile=invalidate_profile,
            )
            return

        stub = CALLBACK_STUB_ANSWER.get(resolved_callback.handler_id)
        if stub is None:
            log.warning("unknown handler_id", handler_id=resolved_callback.handler_id)
            _ = await query.answer()
            return

        _ = await query.answer(stub)
