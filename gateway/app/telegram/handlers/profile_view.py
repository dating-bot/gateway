import asyncio
import html
import urllib.request

import structlog
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    MediaUnion,
)
from dishka.integrations.aiogram import FromDishka

from gateway.app.telegram.fsm.states import EditProfileState
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.protocols.profile import ProfileServiceProtocol
from gateway.usecases.profile.get_profile import GetProfile

log = structlog.stdlib.get_logger("gateway.handlers.profile_view")

_EDIT_MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Имя", callback_data="edit:name")],
        [InlineKeyboardButton(text="Возраст", callback_data="edit:age")],
        [InlineKeyboardButton(text="Город", callback_data="edit:city")],
        [InlineKeyboardButton(text="Био", callback_data="edit:bio")],
        [InlineKeyboardButton(text="📷 Фото", callback_data="profile:photos:menu")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:profile:view")],
    ]
)

_FIELD_PROMPTS = {
    "name": "Введи новое имя (до 64 символов). /cancel — отмена.",
    "age": "Введи новый возраст числом (14–100). /cancel — отмена.",
    "city": "Введи новый город (до 64 символов). /cancel — отмена.",
    "bio": "Введи новое описание (до 500 символов). /cancel — отмена.",
}


async def _fetch_url_bytes(url: str) -> bytes:
    def _read() -> bytes:
        lowered = url.lower()
        if not lowered.startswith(("https://", "http://")):
            msg = "only http(s) presigned URLs are allowed"
            raise ValueError(msg)
        req = urllib.request.Request(url, headers={"User-Agent": "dating-bot-gateway/1.0"})  # noqa: S310
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            return resp.read()

    return await asyncio.to_thread(_read)


def _profile_caption_html(profile_name: str, age: int, city: str, gender_label: str, bio: str) -> str:
    """Telegram HTML: экранируем пользовательский текст, иначе parse_mode ломается и callback не отвечает."""
    return (
        f"👤 <b>{html.escape(profile_name)}</b>, {age}\n"
        f"📍 {html.escape(city)}\n"
        f"👫 {html.escape(gender_label)}\n\n"
        f"{html.escape(bio)}"
    )


async def _send_profile_photos_to_chat(
    bot: Bot,
    chat_id: int,
    text: str,
    buffers: list[BufferedInputFile],
) -> None:
    """Отправить фото альбомом (2–10 за раз) или одним сообщением."""
    if len(buffers) == 1:
        _ = await bot.send_photo(chat_id=chat_id, photo=buffers[0], caption=text, parse_mode="HTML")
        return

    chunk_size = 10
    for start in range(0, len(buffers), chunk_size):
        chunk = buffers[start : start + chunk_size]
        if len(chunk) == 1:
            if start == 0:
                _ = await bot.send_photo(chat_id=chat_id, photo=chunk[0], caption=text, parse_mode="HTML")
            else:
                _ = await bot.send_photo(chat_id=chat_id, photo=chunk[0])
            continue
        media: list[MediaUnion] = []
        for i, buf in enumerate(chunk):
            cap = text if start == 0 and i == 0 else None
            if cap:
                media.append(InputMediaPhoto(media=buf, caption=cap, parse_mode="HTML"))
            else:
                media.append(InputMediaPhoto(media=buf))
        _ = await bot.send_media_group(chat_id=chat_id, media=media)


async def handle_profile_view(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
    profile_service: FromDishka[ProfileServiceProtocol],
) -> None:
    """Показать анкету текущего пользователя (фото по presigned URL + текст)."""
    del resolved
    telegram_id = query.from_user.id
    try:
        await get_profile.invalidate(telegram_id)
        profile = await get_profile.execute(telegram_id)

        if profile is None:
            _ = await query.answer("Профиль не найден. Создай через /start")
            return

        if query.message is None:
            _ = await query.answer("Ошибка сообщения")
            return

        gender_label = {"male": "Мужчина", "female": "Женщина"}.get(profile.gender.value, "—")
        text = _profile_caption_html(profile.name, profile.age, profile.city, gender_label, profile.bio)

        active_photos = [p for p in profile.photos if p.is_active]
        buffers: list[BufferedInputFile] = []

        for ph in active_photos:
            try:
                url = await profile_service.get_presigned_url(ph.photo_id)
                data = await _fetch_url_bytes(url)
                buffers.append(BufferedInputFile(data, filename=f"photo_{ph.photo_id}.jpg"))
            except Exception:
                log.exception("presigned photo fetch failed", photo_id=ph.photo_id)

        bot = query.bot
        if bot is None:
            _ = await query.answer("Ошибка: бот недоступен")
            return

        chat_id = query.message.chat.id

        if not buffers:
            _ = await query.message.answer(text, parse_mode="HTML")
            _ = await query.answer()
            return

        await _send_profile_photos_to_chat(bot, chat_id, text, buffers)
        _ = await query.answer()
    except Exception:
        log.exception("handle_profile_view failed", telegram_id=telegram_id)
        _ = await query.answer("Не удалось показать профиль. Попробуй ещё раз.", show_alert=True)


async def handle_profile_edit(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
) -> None:
    """Показать меню редактирования профиля."""
    del resolved
    telegram_id = query.from_user.id
    profile = await get_profile.execute(telegram_id)
    if profile is None:
        _ = await query.answer("Сначала создай профиль через /start")
        return
    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return
    _ = await query.message.answer("Что хочешь изменить?", reply_markup=_EDIT_MENU_KB)
    _ = await query.answer()


async def handle_edit_field_select(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    state: FSMContext,
    get_profile: FromDishka[GetProfile],
) -> None:
    """Начать ввод нового значения выбранного поля."""
    field = resolved.path_params.get("field", "")
    if field not in _FIELD_PROMPTS:
        _ = await query.answer("Неизвестное поле")
        return

    telegram_id = query.from_user.id
    profile = await get_profile.execute(telegram_id)
    if profile is None:
        _ = await query.answer("Сначала создай профиль через /start")
        return

    await state.set_state(EditProfileState.enter_value)
    _ = await state.update_data(edit_field=field)
    prompt = _FIELD_PROMPTS[field]
    if query.message is not None:
        _ = await query.message.answer(prompt)
    _ = await query.answer()
