"""FSM: регистрация (CreateProfile) и анкета редактирования (UpdateProfile)."""

from typing import Annotated, Final

import structlog
from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dishka import FromDishka

from external_clients.profile_api.v1 import profile_pb2
from gateway.usecases.profile.create_profile import CreateProfile
from gateway.usecases.profile.errors import (
    DuplicateProfileError,
    ProfileNotFoundForMutationError,
    ProfileServiceTransportError,
)
from gateway.usecases.profile.update_profile import UpdateProfile
from gateway.usecases.profile.upload_profile_photo import UploadProfilePhoto

log = structlog.stdlib.get_logger("gateway.app.server.telegram.registration_fsm")

_NAME_MAX: Final = 120
_CITY_MAX: Final = 120
_BIO_MAX: Final = 2000
_AGE_MIN: Final = 14
_AGE_MAX: Final = 120

_MODE_CREATE: Final = "create"
_MODE_UPDATE: Final = "update"


class Registration(StatesGroup):
    name = State()
    age = State()
    city = State()
    bio = State()
    gender = State()


class PhotoPrompt(StatesGroup):
    """После создания/обновления профиля — опциональное фото."""

    waiting = State()


def _gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="М", callback_data="reg:gender:m"),
                InlineKeyboardButton(text="Ж", callback_data="reg:gender:f"),
            ],
        ],
    )


def register_registration_handlers(router: Router) -> None:
    _register_cancel(router)
    _register_name(router)
    _register_age(router)
    _register_city(router)
    _register_bio(router)
    _register_gender(router)
    _register_photo_prompt(router)


def _register_cancel(router: Router) -> None:
    @router.message(Command("cancel"))
    async def cmd_cancel(  # pyright: ignore[reportUnusedFunction]
        message: Message,
        state: FSMContext,
    ) -> None:
        if await state.get_state() is None:
            return
        await state.clear()
        _ = await message.answer("Регистрация отменена. Можно начать снова командой /start. /menu — функции.")


def _register_name(router: Router) -> None:
    @router.message(StateFilter(Registration.name), F.text)
    async def process_name(  # pyright: ignore[reportUnusedFunction]
        message: Message,
        state: FSMContext,
    ) -> None:
        raw = (message.text or "").strip()
        if not raw or len(raw) > _NAME_MAX:
            _ = await message.answer(f"Введи имя (до {_NAME_MAX} символов).")
            return
        await state.update_data(name=raw)
        await state.set_state(Registration.age)
        _ = await message.answer("Сколько тебе лет? (число)")


def _register_age(router: Router) -> None:
    @router.message(StateFilter(Registration.age), F.text)
    async def process_age(  # pyright: ignore[reportUnusedFunction]
        message: Message,
        state: FSMContext,
    ) -> None:
        text = (message.text or "").strip()
        try:
            age = int(text)
        except ValueError:
            _ = await message.answer("Нужно целое число, например 25.")
            return
        if age < _AGE_MIN or age > _AGE_MAX:
            _ = await message.answer(f"Возраст от {_AGE_MIN} до {_AGE_MAX}.")
            return
        await state.update_data(age=age)
        await state.set_state(Registration.city)
        _ = await message.answer("Из какого ты города?")


def _register_city(router: Router) -> None:
    @router.message(StateFilter(Registration.city), F.text)
    async def process_city(  # pyright: ignore[reportUnusedFunction]
        message: Message,
        state: FSMContext,
    ) -> None:
        raw = (message.text or "").strip()
        if not raw or len(raw) > _CITY_MAX:
            _ = await message.answer(f"Введи город (до {_CITY_MAX} символов).")
            return
        await state.update_data(city=raw)
        await state.set_state(Registration.bio)
        _ = await message.answer(
            "Несколько слов о себе (можно отправить «—» если пока не хочешь):",
        )


async def _enter_photo_prompt(message: Message, state: FSMContext, photo_context: str) -> None:
    await state.set_state(PhotoPrompt.waiting)
    await state.update_data(photo_context=photo_context)
    _ = await message.answer(
        "Пришли фото (одно) для анкеты или /skip_photo.\nГеолокацию можно позже: /menu → «Отправить гео».",
    )


def _register_bio(router: Router) -> None:
    @router.message(StateFilter(Registration.bio), F.text)
    async def process_bio(  # pyright: ignore[reportUnusedFunction]
        message: Message,
        state: FSMContext,
        update_profile: Annotated[UpdateProfile, FromDishka()],
    ) -> None:
        raw = (message.text or "").strip()
        if len(raw) > _BIO_MAX:
            _ = await message.answer(f"Короче, до {_BIO_MAX} символов.")
            return
        bio = "" if raw in {"—", "-"} else raw
        await state.update_data(bio=bio)
        data = await state.get_data()
        mode = data.get("mode", _MODE_CREATE)
        if mode == _MODE_UPDATE:
            await _finish_bio_update(message, state, data, update_profile)
            return
        await state.set_state(Registration.gender)
        _ = await message.answer("Укажи пол:", reply_markup=_gender_keyboard())


async def _finish_bio_update(
    message: Message,
    state: FSMContext,
    data: dict[str, object],
    update_profile: UpdateProfile,
) -> None:
    if message.from_user is None:
        return
    try:
        _ = await update_profile.execute(
            UpdateProfile.Request(
                telegram_id=message.from_user.id,
                name=str(data["name"]),
                age=int(data["age"]),
                city=str(data["city"]),
                bio=str(data.get("bio", "")),
            ),
        )
    except ProfileNotFoundForMutationError:
        await state.clear()
        _ = await message.answer("Профиль не найден. Напиши /start.")
        return
    except ProfileServiceTransportError:
        log.exception("update_profile failed")
        await state.clear()
        _ = await message.answer("Не удалось обновить профиль. Попробуй позже.")
        return
    await _enter_photo_prompt(message, state, "update")


def _register_gender(router: Router) -> None:
    @router.callback_query(StateFilter(Registration.gender), F.data.in_({"reg:gender:m", "reg:gender:f"}))
    async def process_gender(  # pyright: ignore[reportUnusedFunction]
        query: CallbackQuery,
        state: FSMContext,
        create_profile: Annotated[CreateProfile, FromDishka()],
    ) -> None:
        if query.from_user is None:
            _ = await query.answer()
            return
        gender = profile_pb2.GENDER_MALE if query.data == "reg:gender:m" else profile_pb2.GENDER_FEMALE
        data = await state.get_data()
        _ = await query.answer()
        try:
            await create_profile.execute(
                CreateProfile.Request(
                    telegram_id=query.from_user.id,
                    name=str(data["name"]),
                    age=int(data["age"]),
                    city=str(data["city"]),
                    bio=str(data.get("bio", "")),
                    gender=int(gender),
                ),
            )
        except DuplicateProfileError:
            await state.clear()
            msg = query.message
            if msg is not None:
                _ = await msg.answer("Профиль уже существует. Напиши /start.")
            return
        except ProfileServiceTransportError:
            log.exception("create_profile failed")
            msg = query.message
            if msg is not None:
                _ = await msg.answer("Не удалось сохранить профиль. Попробуй позже или /start.")
            await state.clear()
            return

        msg = query.message
        if msg is not None:
            await state.set_state(PhotoPrompt.waiting)
            await state.update_data(photo_context="create")
            _ = await msg.answer(
                "Профиль создан. Пришли фото для анкеты или /skip_photo.\nГеолокацию можно позже: /menu",
            )
        else:
            await state.clear()


def _register_photo_prompt(router: Router) -> None:
    @router.message(StateFilter(PhotoPrompt.waiting), Command("skip_photo"))
    async def skip_photo_step(  # pyright: ignore[reportUnusedFunction]
        message: Message,
        state: FSMContext,
    ) -> None:
        await state.clear()
        _ = await message.answer("Без фото. Команды: /menu — все функции, гео — кнопка «Отправить гео».")

    @router.message(StateFilter(PhotoPrompt.waiting), F.photo)
    async def save_profile_photo(  # pyright: ignore[reportUnusedFunction]
        message: Message,
        state: FSMContext,
        bot: Bot,
        upload: Annotated[UploadProfilePhoto, FromDishka()],
    ) -> None:
        if message.from_user is None or not message.photo:
            return
        photo = message.photo[-1]
        try:
            buf = await bot.download(photo)
            raw = buf.read()
        except Exception:
            log.exception("telegram photo download failed")
            _ = await message.answer("Не удалось скачать фото. Попробуй другое или /skip_photo.")
            return
        try:
            _ = await upload.execute(
                UploadProfilePhoto.Request(
                    telegram_id=message.from_user.id,
                    data=raw,
                    content_type="image/jpeg",
                ),
            )
        except ProfileServiceTransportError:
            log.exception("upload_profile_photo failed")
            await state.clear()
            _ = await message.answer("Не удалось сохранить фото. /start")
            return
        await state.clear()
        _ = await message.answer("Фото сохранено. /menu — функции и геолокация.")
