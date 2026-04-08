from aiogram import F, Router
from aiogram.types import Message, ReplyKeyboardRemove
from dishka.integrations.aiogram import FromDishka

from gateway.usecases.profile.get_profile import GetProfile
from gateway.usecases.profile.set_geo import SetGeo

geo_router = Router(name="geo")


@geo_router.message(F.location)
async def handle_location(
    message: Message,
    set_geo: FromDishka[SetGeo],
    get_profile: FromDishka[GetProfile],
) -> None:
    if message.from_user is None or message.location is None:
        return

    telegram_id = message.from_user.id
    profile = await get_profile.execute(telegram_id)
    if profile is None:
        _ = await message.answer("Сначала создай профиль через /start.")
        return

    loc = message.location
    await set_geo.execute(telegram_id=telegram_id, latitude=loc.latitude, longitude=loc.longitude)
    _ = await message.answer("Геолокация сохранена 📍", reply_markup=ReplyKeyboardRemove())
