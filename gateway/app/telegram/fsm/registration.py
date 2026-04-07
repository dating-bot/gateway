"""FSM создания профиля: 5 шагов — name → age → city → bio → gender → (photo prompt).

Диспетчер инжектирует usecase CreateProfile через dishka.
"""

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from dishka.integrations.aiogram import FromDishka

from gateway.app.telegram.fsm.states import PhotoPromptState, RegistrationState
from gateway.domain.profile import Gender
from gateway.usecases.profile.create_profile import CreateProfile
from gateway.usecases.profile.upload_photo import UploadPhoto

registration_router = Router(name="registration_fsm")

_GENDER_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Мужчина"), KeyboardButton(text="Женщина")]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

_GENDER_TEXT_MAP: dict[str, Gender] = {
    "мужчина": Gender.MALE,
    "женщина": Gender.FEMALE,
}


@registration_router.message(StateFilter(RegistrationState.enter_name))
async def handle_enter_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 64:
        await message.answer("Введи имя (до 64 символов):")
        return
    await state.update_data(name=name)
    await state.set_state(RegistrationState.enter_age)
    await message.answer("Отлично! Теперь введи возраст:")


@registration_router.message(StateFilter(RegistrationState.enter_age))
async def handle_enter_age(message: Message, state: FSMContext) -> None:
    try:
        age = int((message.text or "").strip())
        if not (14 <= age <= 100):  # noqa: PLR2004
            raise ValueError
    except ValueError:
        await message.answer("Введи возраст числом (от 14 до 100):")
        return
    await state.update_data(age=age)
    await state.set_state(RegistrationState.enter_city)
    await message.answer("Укажи город:")


@registration_router.message(StateFilter(RegistrationState.enter_city))
async def handle_enter_city(message: Message, state: FSMContext) -> None:
    city = (message.text or "").strip()
    if not city or len(city) > 64:
        await message.answer("Введи название города (до 64 символов):")
        return
    await state.update_data(city=city)
    await state.set_state(RegistrationState.enter_bio)
    await message.answer("Расскажи немного о себе (bio):")


@registration_router.message(StateFilter(RegistrationState.enter_bio))
async def handle_enter_bio(message: Message, state: FSMContext) -> None:
    bio = (message.text or "").strip()
    if not bio or len(bio) > 500:  # noqa: PLR2004
        await message.answer("Расскажи о себе (до 500 символов):")
        return
    await state.update_data(bio=bio)
    await state.set_state(RegistrationState.enter_gender)
    await message.answer("Укажи пол:", reply_markup=_GENDER_KB)


@registration_router.message(StateFilter(RegistrationState.enter_gender))
async def handle_enter_gender(
    message: Message,
    state: FSMContext,
    create_profile: FromDishka[CreateProfile],
) -> None:
    text = (message.text or "").strip().lower()
    gender = _GENDER_TEXT_MAP.get(text)
    if gender is None:
        await message.answer("Выбери пол из кнопок ниже:", reply_markup=_GENDER_KB)
        return

    data = await state.get_data()
    await state.update_data(gender=gender.value)

    telegram_id = message.from_user.id if message.from_user else 0
    await create_profile.execute(
        CreateProfile.Request(
            telegram_id=telegram_id,
            name=data["name"],
            age=data["age"],
            city=data["city"],
            bio=data["bio"],
            gender=gender,
        )
    )

    await state.set_state(PhotoPromptState.waiting_photo)
    await message.answer(
        "Профиль создан! 🎉\n\nТеперь загрузи фото (или отправь /skip чтобы пропустить):",
        reply_markup=ReplyKeyboardRemove(),
    )


@registration_router.message(StateFilter(PhotoPromptState.waiting_photo), F.photo)
async def handle_photo_upload(
    message: Message,
    state: FSMContext,
    upload_photo: FromDishka[UploadPhoto],
) -> None:
    if not message.photo:
        return
    largest = message.photo[-1]
    bot = message.bot
    if bot is None:
        return
    file = await bot.get_file(largest.file_id)
    if file.file_path is None:
        await message.answer("Не удалось получить файл. Попробуй ещё раз.")
        return
    file_bytes = await bot.download_file(file.file_path)
    if file_bytes is None:
        await message.answer("Не удалось скачать файл. Попробуй ещё раз.")
        return
    data = file_bytes.read()

    telegram_id = message.from_user.id if message.from_user else 0
    await upload_photo.execute(telegram_id=telegram_id, data=data)

    await state.clear()
    await message.answer("Фото загружено! Профиль готов ✅\n\nИспользуй /menu для навигации.")


@registration_router.message(StateFilter(PhotoPromptState.waiting_photo), F.text == "/skip")
async def handle_photo_skip(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Профиль создан без фото ✅\n\nИспользуй /menu для навигации.")
