"""Управление фото профиля: список, добавление, удаление."""

import structlog
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dishka.integrations.aiogram import FromDishka
from grpclib import GRPCError, Status

from gateway.app.telegram.fsm.states import PhotoManageState
from gateway.domain.profile import Profile
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.usecases.profile.delete_photo import DeletePhoto
from gateway.usecases.profile.get_profile import GetProfile
from gateway.usecases.profile.upload_photo import UploadPhoto

log = structlog.stdlib.get_logger("gateway.handlers.profile_photos")

profile_photos_router = Router(name="profile_photos_fsm")


def _photos_menu_text(profile: Profile) -> str:
    n = len([p for p in profile.photos if p.is_active])
    return f"📷 Фото в анкете: <b>{n}</b>\n\nУдали лишнее кнопкой или добавь новое."


def _photos_menu_keyboard(profile: Profile) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for p in profile.photos:
        if not p.is_active:
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 Удалить ({p.photo_id})",
                    callback_data=f"photos:del:{p.photo_id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ Добавить фото", callback_data="photos:add")])
    rows.append([InlineKeyboardButton(text="◀️ Назад к полям", callback_data="menu:profile:edit")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def handle_profile_photos_menu(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
) -> None:
    del resolved
    telegram_id = query.from_user.id
    profile = await get_profile.execute(telegram_id)
    if profile is None:
        _ = await query.answer("Сначала создай профиль через /start")
        return
    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return

    text = _photos_menu_text(profile)
    kb = _photos_menu_keyboard(profile)
    _ = await query.message.answer(text, parse_mode="HTML", reply_markup=kb)
    _ = await query.answer()


async def handle_photos_add(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    state: FSMContext,
) -> None:
    del resolved
    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return
    await state.set_state(PhotoManageState.waiting_photo)
    _ = await query.message.answer("Пришли фото одним сообщением (или /cancel).")
    _ = await query.answer()


async def handle_photos_delete(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    delete_photo: FromDishka[DeletePhoto],
    get_profile: FromDishka[GetProfile],
) -> None:
    raw_id = resolved.path_params.get("photo_id", "")
    try:
        photo_id = int(raw_id)
    except ValueError:
        _ = await query.answer("Некорректный id")
        return

    telegram_id = query.from_user.id
    try:
        await delete_photo.execute(telegram_id, photo_id)
    except GRPCError as e:
        if e.status == Status.NOT_FOUND:
            _ = await query.answer("Фото уже удалено или не найдено", show_alert=True)
        else:
            log.exception("delete photo grpc", status=e.status)
            _ = await query.answer("Не удалось удалить", show_alert=True)
        return
    except Exception:
        log.exception("delete photo failed", photo_id=photo_id)
        _ = await query.answer("Ошибка удаления", show_alert=True)
        return

    profile = await get_profile.execute(telegram_id)
    if profile is None or query.message is None:
        _ = await query.answer("Готово")
        return

    text = _photos_menu_text(profile)
    kb = _photos_menu_keyboard(profile)
    try:
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        _ = await query.message.answer(text, parse_mode="HTML", reply_markup=kb)
    _ = await query.answer("Удалено")


@profile_photos_router.message(StateFilter(PhotoManageState.waiting_photo), Command("cancel"))
async def handle_photo_add_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    _ = await message.answer("Добавление фото отменено.")


@profile_photos_router.message(StateFilter(PhotoManageState.waiting_photo), F.photo)
async def handle_photo_add_upload(
    message: Message,
    state: FSMContext,
    upload_photo: FromDishka[UploadPhoto],
) -> None:
    if not message.photo:
        return
    if message.from_user is None:
        return
    largest = message.photo[-1]
    bot = message.bot
    if bot is None:
        return
    file = await bot.get_file(largest.file_id)
    if file.file_path is None:
        _ = await message.answer("Не удалось получить файл.")
        return
    file_bytes = await bot.download_file(file.file_path)
    if file_bytes is None:
        _ = await message.answer("Не удалось скачать файл.")
        return
    data = file_bytes.read()
    content_type = "image/jpeg"
    telegram_id = message.from_user.id
    try:
        _ = await upload_photo.execute(telegram_id=telegram_id, data=data, content_type=content_type)
    except Exception:
        log.exception("upload in manage menu failed", telegram_id=telegram_id)
        _ = await message.answer("Не удалось загрузить фото. Попробуй ещё или /cancel.")
        return

    await state.clear()
    _ = await message.answer("Фото добавлено ✅\n\nОткрой «✏️ Редактировать» → «📷 Фото», если нужно ещё.")


@profile_photos_router.message(StateFilter(PhotoManageState.waiting_photo))
async def handle_photo_add_non_photo(message: Message) -> None:
    _ = await message.answer("Нужно отправить фото. /cancel — отмена.")
