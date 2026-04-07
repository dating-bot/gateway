from typing import Annotated

import aiohttp
import structlog
from aiogram import Bot, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InputMediaPhoto, Message
from dishka import FromDishka

from gateway.app.server.telegram.callback_replies import CALLBACK_STUB_ANSWER
from gateway.app.server.telegram.geo_menu import register_geo_and_menu
from gateway.app.server.telegram.registration_fsm import Registration, register_registration_handlers
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.protocols.profile.protocol import ProfileServiceProtocol
from gateway.usecases.profile.get_profile import GetProfile
from gateway.usecases.profile.invalidate_profile import InvalidateProfile

log = structlog.stdlib.get_logger("gateway.app.server.telegram.handlers")

_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=45)


async def _http_get_bytes(session: aiohttp.ClientSession, url: str) -> bytes | None:
    """Скачать файл по URL на gateway (MinIO может быть недоступен с серверов Telegram)."""
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                log.warning("photo fetch http status", status=resp.status, url_prefix=url[:96])
                return None
            return await resp.read()
    except Exception:
        log.exception("photo fetch failed", url_prefix=url[:96])
        return None


async def _send_profile_view(
    message: Message,
    *,
    bot: Bot,
    get_profile: GetProfile,
    invalidate_profile: InvalidateProfile,
    profile_service: ProfileServiceProtocol,
    telegram_id: int,
) -> None:
    await invalidate_profile.execute(InvalidateProfile.Request(telegram_id=telegram_id))
    response = await get_profile.execute(GetProfile.Request(telegram_id=telegram_id))
    if response.profile is None:
        _ = await message.answer("Профиль не найден")
        return
    p = response.profile
    lines: list[str] = [
        f"👤 {p.name}",
        f"Возраст: {p.age}",
        f"Город: {p.city}",
    ]
    if p.bio.strip():
        lines.extend(["", "О себе:", p.bio])
    if p.latitude is not None and p.longitude is not None:
        lines.extend(["", f"📍 Координаты: {p.latitude:.5f}, {p.longitude:.5f}"])
    _ = await message.answer("\n".join(lines))

    files: list[BufferedInputFile] = []
    async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as http:
        for photo_id in p.photo_ids[:10]:
            try:
                url = await profile_service.get_presigned_url(photo_id)
                if not url:
                    continue
                raw = await _http_get_bytes(http, url)
                if raw is None:
                    continue
                files.append(BufferedInputFile(raw, filename=f"profile_{photo_id}.jpg"))
            except Exception:
                log.exception("profile photo pipeline failed", photo_id=photo_id)

    if len(files) == 1:
        _ = await message.answer_photo(files[0])
    elif len(files) > 1:
        media = [InputMediaPhoto(media=f) for f in files]
        _ = await bot.send_media_group(chat_id=message.chat.id, media=media)


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
        bot: Annotated[Bot, FromDishka()],
        get_profile: Annotated[GetProfile, FromDishka()],
        invalidate_profile: Annotated[InvalidateProfile, FromDishka()],
        profile_service: Annotated[ProfileServiceProtocol, FromDishka()],
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
            msg = query.message
            if msg is None:
                _ = await query.answer("Сообщение устарело", show_alert=True)
                return
            _ = await query.answer()
            await _send_profile_view(
                msg,
                bot=bot,
                get_profile=get_profile,
                invalidate_profile=invalidate_profile,
                profile_service=profile_service,
                telegram_id=user_id,
            )
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
