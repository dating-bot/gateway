"""Обработчики просмотра и редактирования профиля."""

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from dishka.integrations.aiogram import FromDishka

from gateway.domain.resolved_callback import ResolvedCallback
from gateway.usecases.profile.get_profile import GetProfile

_EDIT_MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Имя", callback_data="edit:name")],
        [InlineKeyboardButton(text="Возраст", callback_data="edit:age")],
        [InlineKeyboardButton(text="Город", callback_data="edit:city")],
        [InlineKeyboardButton(text="Био", callback_data="edit:bio")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:profile:view")],
    ]
)


async def handle_profile_view(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
) -> None:
    """Показать анкету текущего пользователя."""
    telegram_id = query.from_user.id
    # Инвалидируем кэш чтобы показать актуальные данные
    await get_profile.invalidate(telegram_id)
    profile = await get_profile.execute(telegram_id)

    if profile is None:
        await query.answer("Профиль не найден. Создай через /start")
        return

    gender_label = {"male": "Мужчина", "female": "Женщина"}.get(profile.gender.value, "—")
    text = f"👤 <b>{profile.name}</b>, {profile.age}\n📍 {profile.city}\n👫 {gender_label}\n\n{profile.bio}"
    await query.message.answer(text, parse_mode="HTML")  # type: ignore[union-attr]
    await query.answer()


async def handle_profile_edit(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
) -> None:
    """Войти в меню редактирования профиля."""
    telegram_id = query.from_user.id
    profile = await get_profile.execute(telegram_id)
    if profile is None:
        await query.answer("Сначала создай профиль через /start")
        return
    await query.message.answer("Что хочешь изменить?", reply_markup=_EDIT_MENU_KB)  # type: ignore[union-attr]
    await query.answer()
