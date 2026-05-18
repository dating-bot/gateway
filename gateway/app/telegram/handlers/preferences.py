import time
from datetime import UTC, datetime, timedelta

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from dishka.integrations.aiogram import FromDishka

from gateway.domain.profile import Gender, Profile, SubscriptionTier
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.infra.telegram import TelegramConfig
from gateway.protocols.cache import CacheProtocol
from gateway.protocols.profile import ProfileServiceProtocol
from gateway.usecases.profile.get_profile import GetProfile

_DEFAULT_PREFS = ProfileServiceProtocol.Preferences(
    gender_pref=Gender.ANY,
    age_min=18,
    age_max=50,
    max_distance_km=50,
)
_PAUSE_TTL = timedelta(days=3650)
_DISTANCE_PRESETS = (10, 30, 50, 100)


def _paused_key(telegram_id: int) -> str:
    return f"profile:paused:{telegram_id}"


async def _is_paused(cache: CacheProtocol, telegram_id: int) -> bool:
    return (await cache.get(_paused_key(telegram_id), unmarshal_as=int)) is not None


def _settings_root_kb(*, paused: bool) -> InlineKeyboardMarkup:
    profile_button = "▶️ Анкета: включить" if paused else "⏸ Анкета: пауза"
    profile_action = "settings:profile:resume" if paused else "settings:profile:pause"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔎 Поиск", callback_data="settings:search")],
            [InlineKeyboardButton(text=profile_button, callback_data=profile_action)],
            [InlineKeyboardButton(text="💎 Premium", callback_data="settings:premium")],
            [
                InlineKeyboardButton(text="🛟 Поддержка", callback_data="settings:support"),
                InlineKeyboardButton(text="📄 Условия", callback_data="settings:terms"),
            ],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="menu:main")],
        ]
    )


def _search_kb(prefs: ProfileServiceProtocol.Preferences) -> InlineKeyboardMarkup:
    g = prefs.gender_pref
    male = "✅ Мужчины" if g == Gender.MALE else "Мужчины"
    female = "✅ Женщины" if g == Gender.FEMALE else "Женщины"
    any_label = "✅ Все" if g == Gender.ANY else "Все"

    age = f"{prefs.age_min}-{prefs.age_max}"
    age_18_25 = "✅ 18-25" if age == "18-25" else "18-25"
    age_26_35 = "✅ 26-35" if age == "26-35" else "26-35"
    age_36_45 = "✅ 36-45" if age == "36-45" else "36-45"
    age_18_99 = "✅ 18-99" if age == "18-99" else "18-99"

    dist = prefs.max_distance_km
    d10 = "✅ 10 км" if dist == _DISTANCE_PRESETS[0] else "10 км"
    d30 = "✅ 30 км" if dist == _DISTANCE_PRESETS[1] else "30 км"
    d50 = "✅ 50 км" if dist == _DISTANCE_PRESETS[2] else "50 км"
    d100 = "✅ 100 км" if dist == _DISTANCE_PRESETS[3] else "100 км"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Кого ищем:", callback_data="settings:search")],
            [
                InlineKeyboardButton(text=male, callback_data="settings:search:gender:male"),
                InlineKeyboardButton(text=female, callback_data="settings:search:gender:female"),
                InlineKeyboardButton(text=any_label, callback_data="settings:search:gender:any"),
            ],
            [InlineKeyboardButton(text="Возраст:", callback_data="settings:search")],
            [
                InlineKeyboardButton(text=age_18_25, callback_data="settings:search:age:18-25"),
                InlineKeyboardButton(text=age_26_35, callback_data="settings:search:age:26-35"),
            ],
            [
                InlineKeyboardButton(text=age_36_45, callback_data="settings:search:age:36-45"),
                InlineKeyboardButton(text=age_18_99, callback_data="settings:search:age:18-99"),
            ],
            [InlineKeyboardButton(text="Радиус:", callback_data="settings:search")],
            [
                InlineKeyboardButton(text=d10, callback_data="settings:search:distance:10"),
                InlineKeyboardButton(text=d30, callback_data="settings:search:distance:30"),
                InlineKeyboardButton(text=d50, callback_data="settings:search:distance:50"),
                InlineKeyboardButton(text=d100, callback_data="settings:search:distance:100"),
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:settings")],
        ]
    )


def _is_premium_active(profile: Profile | None) -> bool:
    if profile is None or profile.subscription_tier != SubscriptionTier.PREMIUM:
        return False
    expires_at = profile.subscription_expires_at_seconds or 0
    return expires_at > int(time.time())


def _format_expiry(profile: Profile) -> str:
    expires_at = profile.subscription_expires_at_seconds
    if not expires_at:
        return "неизвестно"
    return datetime.fromtimestamp(expires_at, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")


async def _load_preferences(
    profile_service: ProfileServiceProtocol,
    telegram_id: int,
) -> ProfileServiceProtocol.Preferences:
    prefs = await profile_service.get_preferences(telegram_id)
    if prefs is None:
        return _DEFAULT_PREFS
    return prefs


def _search_text(prefs: ProfileServiceProtocol.Preferences) -> str:
    gender = {
        Gender.MALE: "мужчины",
        Gender.FEMALE: "женщины",
        Gender.ANY: "все",
        Gender.UNSPECIFIED: "все",
    }.get(prefs.gender_pref, "все")
    return (
        "⚙️ Поисковые настройки\n\n"
        f"Кого ищешь: {gender}\n"
        f"Возраст: {prefs.age_min}-{prefs.age_max}\n"
        f"Радиус: {prefs.max_distance_km} км\n\n"
        "Выбери готовый вариант:"
    )


async def _show_settings_root(
    query: CallbackQuery,
    get_profile: GetProfile,
    profile_service: ProfileServiceProtocol,
    cache: CacheProtocol,
) -> None:
    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return
    profile = await get_profile.execute(query.from_user.id)
    if profile is None:
        _ = await query.answer("Сначала создай профиль через /start")
        return
    paused = await _is_paused(cache, query.from_user.id)
    fresh_profile = await profile_service.get_profile_by_id(profile.profile_id)
    effective_paused = paused or (fresh_profile is not None and not fresh_profile.is_active)
    status = "⏸ На паузе" if effective_paused else "✅ Активна"
    _ = await query.message.answer(
        f"⚙️ Настройки\n\nСтатус анкеты: {status}\nЗдесь можно управлять поиском, видимостью и Premium.",
        reply_markup=_settings_root_kb(paused=effective_paused),
    )
    _ = await query.answer()


async def handle_settings(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
    profile_service: FromDishka[ProfileServiceProtocol],
    cache: FromDishka[CacheProtocol],
) -> None:
    del resolved
    await _show_settings_root(query, get_profile, profile_service, cache)


async def handle_settings_profile_pause(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
    profile_service: FromDishka[ProfileServiceProtocol],
    cache: FromDishka[CacheProtocol],
) -> None:
    del resolved
    await cache.set(_paused_key(query.from_user.id), 1, ttl=_PAUSE_TTL)
    await _show_settings_root(query, get_profile, profile_service, cache)


async def handle_settings_profile_resume(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
    profile_service: FromDishka[ProfileServiceProtocol],
    cache: FromDishka[CacheProtocol],
) -> None:
    del resolved
    await cache.delete(_paused_key(query.from_user.id))
    await _show_settings_root(query, get_profile, profile_service, cache)


async def handle_settings_search(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    profile_service: FromDishka[ProfileServiceProtocol],
) -> None:
    del resolved
    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return
    prefs = await _load_preferences(profile_service, query.from_user.id)
    _ = await query.message.answer(_search_text(prefs), reply_markup=_search_kb(prefs))
    _ = await query.answer()


async def _save_preferences(
    profile_service: ProfileServiceProtocol,
    telegram_id: int,
    prefs: ProfileServiceProtocol.Preferences,
) -> None:
    await profile_service.set_preferences(
        ProfileServiceProtocol.SetPreferencesRequest(
            telegram_id=telegram_id,
            gender_pref=prefs.gender_pref,
            age_min=prefs.age_min,
            age_max=prefs.age_max,
            max_distance_km=prefs.max_distance_km,
        )
    )


async def handle_settings_search_gender(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    profile_service: FromDishka[ProfileServiceProtocol],
) -> None:
    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return
    prefs = await _load_preferences(profile_service, query.from_user.id)
    gender_raw = resolved.path_params.get("gender", "any").strip().lower()
    gender_map = {
        "male": Gender.MALE,
        "female": Gender.FEMALE,
        "any": Gender.ANY,
    }
    prefs = ProfileServiceProtocol.Preferences(
        gender_pref=gender_map.get(gender_raw, prefs.gender_pref),
        age_min=prefs.age_min,
        age_max=prefs.age_max,
        max_distance_km=prefs.max_distance_km,
    )
    await _save_preferences(profile_service, query.from_user.id, prefs)
    _ = await query.message.answer(_search_text(prefs), reply_markup=_search_kb(prefs))
    _ = await query.answer("Сохранено")


async def handle_settings_search_age(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    profile_service: FromDishka[ProfileServiceProtocol],
) -> None:
    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return
    prefs = await _load_preferences(profile_service, query.from_user.id)
    age_raw = resolved.path_params.get("age", "18-50")
    age_map = {
        "18-25": (18, 25),
        "26-35": (26, 35),
        "36-45": (36, 45),
        "18-99": (18, 99),
    }
    age_min, age_max = age_map.get(age_raw, (prefs.age_min, prefs.age_max))
    prefs = ProfileServiceProtocol.Preferences(
        gender_pref=prefs.gender_pref,
        age_min=age_min,
        age_max=age_max,
        max_distance_km=prefs.max_distance_km,
    )
    await _save_preferences(profile_service, query.from_user.id, prefs)
    _ = await query.message.answer(_search_text(prefs), reply_markup=_search_kb(prefs))
    _ = await query.answer("Сохранено")


async def handle_settings_search_distance(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    profile_service: FromDishka[ProfileServiceProtocol],
) -> None:
    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return
    prefs = await _load_preferences(profile_service, query.from_user.id)
    distance_raw = resolved.path_params.get("km", "50")
    try:
        distance = int(distance_raw)
    except ValueError:
        distance = prefs.max_distance_km
    distance = max(distance, 1)
    distance = min(distance, 200)
    prefs = ProfileServiceProtocol.Preferences(
        gender_pref=prefs.gender_pref,
        age_min=prefs.age_min,
        age_max=prefs.age_max,
        max_distance_km=distance,
    )
    await _save_preferences(profile_service, query.from_user.id, prefs)
    _ = await query.message.answer(_search_text(prefs), reply_markup=_search_kb(prefs))
    _ = await query.answer("Сохранено")


async def handle_settings_premium(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
    config: FromDishka[TelegramConfig],
) -> None:
    del resolved
    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return
    profile = await get_profile.execute(query.from_user.id)
    if profile is None:
        _ = await query.answer("Сначала создай профиль через /start")
        return

    if _is_premium_active(profile):
        tier_text = f"💎 Premium до {_format_expiry(profile)}"
        limits_text = "Лайки: безлимит\nSuper Like: безлимит\nUndo: безлимит"
    else:
        tier_text = "🆓 Free"
        limits_text = (
            f"Лайки: {config.free_like_daily_limit}/день\n"
            f"Super Like: {config.free_super_like_daily_limit}/день\n"
            f"Undo: {config.free_undo_daily_limit}/день"
        )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оформить Premium", callback_data="billing:subscribe")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu:settings")],
        ]
    )
    _ = await query.message.answer(f"💎 Подписка\n\nСтатус: {tier_text}\n\n{limits_text}", reply_markup=kb)
    _ = await query.answer()


async def handle_settings_support(
    query: CallbackQuery,
    resolved: ResolvedCallback,
) -> None:
    del resolved
    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="menu:settings")]])
    _ = await query.message.answer(
        "Поддержка:\n"
        "1) Опиши проблему сообщением в этот чат.\n"
        "2) Или напиши @gipsylll.\n"
        "3) По оплатам приложи скрин и время платежа.",
        reply_markup=kb,
    )
    _ = await query.answer()


async def handle_settings_terms(
    query: CallbackQuery,
    resolved: ResolvedCallback,
) -> None:
    del resolved
    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="menu:settings")]])
    _ = await query.message.answer(
        "Условия использования:\n"
        "1) Подписка активируется после подтвержденного платежа.\n"
        "2) Доступ к Premium действует в течение оплаченного периода.\n"
        "3) Для вопросов по оплатам используй /support.",
        reply_markup=kb,
    )
    _ = await query.answer()
