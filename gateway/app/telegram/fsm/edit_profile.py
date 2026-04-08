from collections.abc import Callable

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from dishka.integrations.aiogram import FromDishka

from gateway.app.telegram.fsm.states import EditProfileState
from gateway.domain.profile import Profile
from gateway.usecases.profile.get_profile import GetProfile
from gateway.usecases.profile.update_profile import UpdateProfile

edit_profile_router = Router(name="edit_profile_fsm")

_EDITABLE_FIELDS = frozenset({"name", "age", "city", "bio"})
_MAX_NAME_CITY = 64
_MAX_BIO = 500
_MIN_AGE = 14
_MAX_AGE = 100


def _merge_name(raw: str, profile: Profile) -> tuple[str, int, str, str] | str:
    if not raw or len(raw) > _MAX_NAME_CITY:
        return "Имя — до 64 символов. Попробуй ещё или /cancel:"
    return (raw, profile.age, profile.city, profile.bio)


def _merge_age(raw: str, profile: Profile) -> tuple[str, int, str, str] | str:
    try:
        age_val = int(raw)
        if not (_MIN_AGE <= age_val <= _MAX_AGE):
            raise ValueError
    except ValueError:
        return "Возраст — число от 14 до 100. Попробуй ещё или /cancel:"
    return (profile.name, age_val, profile.city, profile.bio)


def _merge_city(raw: str, profile: Profile) -> tuple[str, int, str, str] | str:
    if not raw or len(raw) > _MAX_NAME_CITY:
        return "Город — до 64 символов. Попробуй ещё или /cancel:"
    return (profile.name, profile.age, raw, profile.bio)


def _merge_bio(raw: str, profile: Profile) -> tuple[str, int, str, str] | str:
    if not raw or len(raw) > _MAX_BIO:
        return "О себе — до 500 символов. Попробуй ещё или /cancel:"
    return (profile.name, profile.age, profile.city, raw)


_MERGE_BY_FIELD: dict[str, Callable[[str, Profile], tuple[str, int, str, str] | str]] = {
    "name": _merge_name,
    "age": _merge_age,
    "city": _merge_city,
    "bio": _merge_bio,
}


def _merge_edited_field(field: str, raw: str, profile: Profile) -> tuple[str, int, str, str] | str:
    merger = _MERGE_BY_FIELD.get(field)
    if merger is None:
        return "Неизвестное поле."
    return merger(raw, profile)


@edit_profile_router.message(StateFilter(EditProfileState.enter_value), F.text)
async def handle_edit_enter_value(
    message: Message,
    state: FSMContext,
    update_profile: FromDishka[UpdateProfile],
    get_profile: FromDishka[GetProfile],
) -> None:
    if message.from_user is None:
        return

    data = await state.get_data()
    field = data.get("edit_field")
    if field not in _EDITABLE_FIELDS:
        await state.clear()
        _ = await message.answer("Сессия редактирования сброшена. Открой «Редактировать» снова.")
        return

    raw = (message.text or "").strip()
    telegram_id = message.from_user.id
    profile = await get_profile.execute(telegram_id)
    if profile is None:
        await state.clear()
        _ = await message.answer("Профиль не найден. Начни с /start")
        return

    merged = _merge_edited_field(str(field), raw, profile)
    if isinstance(merged, str):
        _ = await message.answer(merged)
        return

    name, age, city, bio = merged
    await update_profile.execute(UpdateProfile.Request(telegram_id=telegram_id, name=name, age=age, city=city, bio=bio))
    await state.clear()
    _ = await message.answer("Изменения сохранены ✅")


@edit_profile_router.message(StateFilter(EditProfileState.enter_value))
async def handle_edit_non_text(message: Message) -> None:
    _ = await message.answer("Сейчас жду текстовое значение. /cancel — отменить редактирование.")
