import structlog
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from gateway.app.telegram.fsm.states import PreferencesState
from gateway.domain.profile import Gender, Profile
from gateway.protocols.profile import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.handlers.preferences")

_GENDER_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ Мужчины", callback_data="pref:gender:m"),
            InlineKeyboardButton(text="💋 Женщины", callback_data="pref:gender:f"),
            InlineKeyboardButton(text="❤️💋 Все", callback_data="pref:gender:any"),
        ],
    ]
)


async def handle_settings(
    message: Message,
    state: FSMContext,
) -> None:
    await state.set_state(PreferencesState.enter_gender_pref)
    _ = await message.answer(
        "⚙️ Настройки предпочтений\n\nКого ищешь?",
        reply_markup=_GENDER_KB,
    )


async def handle_gender_pref(
    message: Message,
    state: FSMContext,
) -> None:
    gender_map = {"m": Gender.MALE, "f": Gender.FEMALE, "any": Gender.ANY}
    gender = gender_map.get(message.text.split(":")[1], Gender.ANY)
    await state.update_data(gender_pref=gender.value)

    await state.set_state(PreferencesState.enter_age_min)
    _ = await message.answer("Минимальный возраст?")


async def handle_age_min(
    message: Message,
    state: FSMContext,
) -> None:
    try:
        age = int(message.text)
        if 18 <= age <= 100:
            await state.update_data(age_min=age)
    except ValueError:
        pass

    await state.set_state(PreferencesState.enter_age_max)
    _ = await message.answer("Максимальный возраст?")


async def handle_age_max(
    message: Message,
    state: FSMContext,
) -> None:
    try:
        age = int(message.text)
        if 18 <= age <= 100:
           _ = await state.update_data(age_max=age)
    except ValueError:
        pass

    await state.set_state(PreferencesState.enter_max_distance)
    _ = await message.answer("Максимальное расстояние (км)?")


async def handle_max_distance(
    message: Message,
    state: FSMContext,
    profile_service: ProfileServiceProtocol,
) -> None:
    user_id = message.from_user.id if message.from_user else 0

    try:
        distance = int(message.text)
        if distance > 0:
            _ = await state.update_data(max_distance_km=distance)
    except ValueError:
        pass

    data = await state.get_data()
    await state.clear()

    try:
        await profile_service.set_preferences(
            ProfileServiceProtocol.SetPreferencesRequest(
                telegram_id=user_id,
                gender_pref=Gender(data.get("gender_pref", "any")),
                age_min=int(data.get("age_min", 18)),
                age_max=int(data.get("age_max", 50)),
                max_distance_km=int(data.get("max_distance_km", 50))),
            )
        )
        answer = "✅ Настройки сохранены!"
    except Exception:
        log.exception("save preferences failed", user_id=user_id)
        answer = "❌ Ошибка сохранения"

    _ = await message.answer(answer)
