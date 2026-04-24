import structlog
from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from dishka.integrations.aiogram import FromDishka

from gateway.app.telegram.fsm.states import RegistrationState
from gateway.app.telegram.handlers.profile_view import (
    _fetch_url_bytes,
    _profile_caption_html,
    _send_profile_photos_to_chat,
)
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.protocols.cache import CacheProtocol
from gateway.protocols.profile import ProfileServiceProtocol
from gateway.protocols.ranking_service import RankingServiceProtocol
from gateway.usecases.dating.check_status import CheckDatingStatus
from gateway.usecases.profile.get_profile import GetProfile

commands_router = Router(name="commands")
log = structlog.stdlib.get_logger("gateway.handlers.commands")

_MAIN_MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🔥 Лента", callback_data="menu:browse"),
        ],
        [
            InlineKeyboardButton(text="👤 Мой профиль", callback_data="menu:profile:view"),
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="menu:profile:edit"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
            InlineKeyboardButton(text="💎 Подписка", callback_data="billing:subscribe"),
        ],
        [
            InlineKeyboardButton(text="➕ Еще", callback_data="menu:more"),
        ],
    ]
)

_GEO_REPLY_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📍 Отправить гео", request_location=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

_MORE_MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Проверка: лента и мэтчи", callback_data="menu:dating:status")],
        [InlineKeyboardButton(text="📍 Отправить гео", callback_data="menu:geo:request")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:main")],
    ]
)


@commands_router.message(Command("start"))
async def handle_start(
    message: Message,
    state: FSMContext,
    get_profile: FromDishka[GetProfile],
) -> None:
    telegram_id = message.from_user.id if message.from_user else 0
    profile = await get_profile.execute(telegram_id)

    if profile is not None:
        await state.clear()
        _ = await message.answer(
            f"С возвращением, {profile.name}! 👋",
            reply_markup=_MAIN_MENU_KB,
        )
        return

    await state.set_state(RegistrationState.enter_name)
    _ = await message.answer("Привет! 👋 Давай создадим твой профиль.\n\nКак тебя зовут?")


@commands_router.message(Command("menu"))
async def handle_menu(
    message: Message,
    state: FSMContext,
    get_profile: FromDishka[GetProfile],
) -> None:
    telegram_id = message.from_user.id if message.from_user else 0
    profile = await get_profile.execute(telegram_id)

    if profile is None:
        _ = await message.answer("Сначала создай профиль через /start")
        return

    await state.clear()
    _ = await message.answer("Главное меню:", reply_markup=_MAIN_MENU_KB)


@commands_router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        _ = await message.answer("Нечего отменять.")
        return
    await state.clear()
    _ = await message.answer("Действие отменено.")


def _build_browse_kb(profile_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❤️", callback_data=f"like:{profile_id}"),
                InlineKeyboardButton(text="👎", callback_data=f"skip:{profile_id}"),
                InlineKeyboardButton(text="⭐", callback_data=f"super_like:{profile_id}"),
            ],
            [
                InlineKeyboardButton(text="↩️", callback_data="undo:last"),
            ],
        ]
    )


async def _send_candidate_profile(
    *,
    bot: Bot,
    chat_id: int,
    candidate,
    profile_service: FromDishka[ProfileServiceProtocol],
    queue_len: int | None = None,
) -> None:
    gender_label = {"male": "Мужчина", "female": "Женщина"}.get(candidate.gender.value, "—")
    text = _profile_caption_html(candidate.name, candidate.age, candidate.city, gender_label, candidate.bio)
    active_photos = [p for p in candidate.photos if p.is_active]
    buffers = []

    for ph in active_photos:
        try:
            url = await profile_service.get_presigned_url(ph.photo_id)
            data = await _fetch_url_bytes(url)
            buffers.append(BufferedInputFile(data, filename=f"candidate_{ph.photo_id}.jpg"))
        except Exception:
            log.exception("candidate photo fetch failed", telegram_id=candidate.telegram_id, photo_id=ph.photo_id)

    if queue_len is not None:
        text = f"{text}\n\nОсталось в очереди: {queue_len}"

    try:
        if not buffers:
            _ = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=_build_browse_kb(candidate.telegram_id),
            )
            return

        await _send_profile_photos_to_chat(bot, chat_id, text, buffers)
        _ = await bot.send_message(
            chat_id=chat_id, text="Выбери действие:", reply_markup=_build_browse_kb(candidate.telegram_id)
        )
    except Exception:
        log.exception("candidate media send failed, falling back to text only", candidate_telegram_id=candidate.telegram_id)
        _ = await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=_build_browse_kb(candidate.telegram_id),
        )


async def _send_next_candidate(  # noqa: PLR0913
    *,
    telegram_id: int,
    message: Message,
    get_profile: FromDishka[GetProfile],
    profile_service: FromDishka[ProfileServiceProtocol],
    ranking_service: FromDishka[RankingServiceProtocol],
    cache: FromDishka[CacheProtocol] | None = None,
    exclude_candidate_ids: set[int] | None = None,
) -> int | None:
    profile = await get_profile.execute(telegram_id)

    if profile is None:
        _ = await message.answer("Сначала создай профиль через /start")
        return None

    max_attempts = 10
    result: tuple[int, int] | None = None
    for _ in range(max_attempts):
        result = await ranking_service.get_next_candidate(telegram_id)
        if result is None:
            break
        candidate_telegram_id, _queue_len = result
        if exclude_candidate_ids and candidate_telegram_id in exclude_candidate_ids:
            log.info(
                "excluded candidate returned, retrying next",
                telegram_id=telegram_id,
                candidate_telegram_id=candidate_telegram_id,
            )
            continue
        if cache is not None:
            seen_key = f"seen:{telegram_id}:{candidate_telegram_id}"
            already_seen = await cache.get(seen_key, unmarshal_as=int)
            if already_seen is not None:
                log.info(
                    "recently seen candidate returned, retrying next",
                    telegram_id=telegram_id,
                    candidate_telegram_id=candidate_telegram_id,
                )
                continue
        break

    if result is None:
        log.info("no next candidate returned", telegram_id=telegram_id)
        _ = await message.answer("Анкеты закончились 🔍 Попробуй позже!")
        return None

    candidate_telegram_id, queue_len = result
    log.info(
        "sending next candidate to telegram",
        telegram_id=telegram_id,
        candidate_telegram_id=candidate_telegram_id,
        queue_len=queue_len,
    )
    candidate = await profile_service.get_profile(candidate_telegram_id)
    if candidate is None:
        log.warning("candidate profile not found", telegram_id=telegram_id, candidate_telegram_id=candidate_telegram_id)
        _ = await message.answer(
            f"Кандидат #{candidate_telegram_id}\nОсталось в очереди: {queue_len}",
            reply_markup=_build_browse_kb(candidate_telegram_id),
        )
        return candidate_telegram_id

    await _send_candidate_profile(
        bot=message.bot,
        chat_id=message.chat.id,
        candidate=candidate,
        profile_service=profile_service,
        queue_len=queue_len,
    )
    return candidate_telegram_id


@commands_router.message(Command("browse"))
async def handle_browse(
    message: Message,
    get_profile: FromDishka[GetProfile],
    profile_service: FromDishka[ProfileServiceProtocol],
    ranking_service: FromDishka[RankingServiceProtocol],
    cache: FromDishka[CacheProtocol],
) -> None:
    telegram_id = message.from_user.id if message.from_user else 0
    await _send_next_candidate(
        telegram_id=telegram_id,
        message=message,
        get_profile=get_profile,
        profile_service=profile_service,
        ranking_service=ranking_service,
        cache=cache,
    )


async def handle_menu_browse(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
    profile_service: FromDishka[ProfileServiceProtocol],
    ranking_service: FromDishka[RankingServiceProtocol],
    cache: FromDishka[CacheProtocol],
) -> None:
    del resolved

    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return

    await _send_next_candidate(
        telegram_id=query.from_user.id,
        message=query.message,
        get_profile=get_profile,
        profile_service=profile_service,
        ranking_service=ranking_service,
        cache=cache,
    )
    _ = await query.answer()


async def handle_menu_more(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
) -> None:
    del resolved

    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return

    profile = await get_profile.execute(query.from_user.id)
    if profile is None:
        _ = await query.answer("Сначала создай профиль через /start")
        return

    _ = await query.message.answer("Дополнительное меню:", reply_markup=_MORE_MENU_KB)
    _ = await query.answer()


async def handle_menu_main(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
) -> None:
    del resolved

    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return

    profile = await get_profile.execute(query.from_user.id)
    if profile is None:
        _ = await query.answer("Сначала создай профиль через /start")
        return

    _ = await query.message.answer("Главное меню:", reply_markup=_MAIN_MENU_KB)
    _ = await query.answer()


async def handle_menu_geo_request(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
) -> None:
    del resolved

    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return

    profile = await get_profile.execute(query.from_user.id)
    if profile is None:
        _ = await query.answer("Сначала создай профиль через /start")
        return

    _ = await query.message.answer(
        "Нажми кнопку ниже, чтобы отправить геолокацию.",
        reply_markup=_GEO_REPLY_KB,
    )
    _ = await query.answer()


async def handle_menu_dating_status(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
    check_dating_status: FromDishka[CheckDatingStatus],
) -> None:
    del resolved

    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return

    profile = await get_profile.execute(query.from_user.id)
    if profile is None:
        _ = await query.answer("Сначала создай профиль через /start")
        return

    result = await check_dating_status.execute(
        CheckDatingStatus.Request(telegram_id=query.from_user.id)
    )
    _ = await query.message.answer(result.text, parse_mode="HTML", reply_markup=_MORE_MENU_KB)
    _ = await query.answer()
