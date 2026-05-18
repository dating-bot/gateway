import json
import time
from datetime import UTC, datetime, timedelta

import structlog
from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from dishka.integrations.aiogram import FromDishka

from gateway.domain.profile import Profile, SubscriptionTier
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.infra.telegram import TelegramConfig
from gateway.protocols.cache import CacheProtocol
from gateway.protocols.events import EventPublisherProtocol
from gateway.protocols.profile import ProfileServiceProtocol
from gateway.usecases.profile.get_profile import GetProfile

payments_router = Router(name="payments")
log = structlog.stdlib.get_logger("gateway.handlers.payments")

_PAYMENT_STARS_CALLBACK = "billing:subscribe:stars"
_PAYMENT_PROVIDER_CALLBACK = "billing:subscribe:provider"
_PAYLOAD_PARTS_MIN = 4


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


async def _ensure_can_buy(
    *,
    telegram_id: int,
    get_profile: GetProfile,
    query: CallbackQuery,
) -> bool:
    profile = await get_profile.execute(telegram_id)
    if not _is_premium_active(profile):
        return True
    _ = await query.answer("Premium уже активен")
    if query.message is not None:
        expiry = _format_expiry(profile)
        _ = await query.message.answer(f"У тебя уже активен Premium до {expiry}. Повторная покупка пока недоступна.")
    return False


def _build_payload(config: TelegramConfig, telegram_id: int) -> str:
    # prefix:telegram_id:duration_days:epoch
    return f"{config.subscription_payload_prefix}:{telegram_id}:{config.subscription_duration_days}:{int(time.time())}"


def _parse_payload(payload: str, config: TelegramConfig) -> tuple[int, int] | None:
    parts = payload.split(":")
    if len(parts) < _PAYLOAD_PARTS_MIN:
        return None
    if parts[0] != config.subscription_payload_prefix:
        return None
    try:
        telegram_id = int(parts[1])
        duration_days = int(parts[2])
    except ValueError:
        return None
    if duration_days <= 0:
        return None
    return telegram_id, duration_days


async def handle_subscribe(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
    config: FromDishka[TelegramConfig],
) -> None:
    del resolved
    del config

    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return
    if not await _ensure_can_buy(telegram_id=query.from_user.id, get_profile=get_profile, query=query):
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Оплатить Stars", callback_data=_PAYMENT_STARS_CALLBACK)],
            [InlineKeyboardButton(text="💳 Оплатить ЮMoney", callback_data=_PAYMENT_PROVIDER_CALLBACK)],
        ]
    )
    _ = await query.message.answer(
        "Premium включает:\n• безлимитный Super Like\n• безлимитный Undo\n\nВыбери способ оплаты:",
        reply_markup=kb,
    )
    _ = await query.answer()


async def _send_subscription_invoice(
    *,
    query: CallbackQuery,
    get_profile: GetProfile,
    config: TelegramConfig,
    mode: str,
) -> None:
    if query.message is None:
        _ = await query.answer("Ошибка сообщения")
        return
    if not await _ensure_can_buy(telegram_id=query.from_user.id, get_profile=get_profile, query=query):
        return

    payload = _build_payload(config, query.from_user.id)

    provider_token = ""
    currency = "XTR"
    amount = config.stars_amount

    if mode == "provider":
        if not config.provider_token:
            log.error("provider payment mode selected, but provider_token is missing")
            _ = await query.answer("Платежи временно недоступны")
            return
        provider_token = config.provider_token
        currency = config.provider_currency
        amount = config.provider_amount

    prices = [LabeledPrice(label=config.subscription_title, amount=amount)]

    await query.bot.send_invoice(
        chat_id=query.from_user.id,
        title=config.subscription_title,
        description=config.subscription_description,
        payload=payload,
        provider_token=provider_token,
        currency=currency,
        prices=prices,
    )
    _ = await query.answer("Счёт отправлен")


async def handle_subscribe_stars(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
    config: FromDishka[TelegramConfig],
) -> None:
    del resolved
    await _send_subscription_invoice(query=query, get_profile=get_profile, config=config, mode="stars")


async def handle_subscribe_provider(
    query: CallbackQuery,
    resolved: ResolvedCallback,
    get_profile: FromDishka[GetProfile],
    config: FromDishka[TelegramConfig],
) -> None:
    del resolved
    await _send_subscription_invoice(query=query, get_profile=get_profile, config=config, mode="provider")


@payments_router.pre_checkout_query()
async def handle_pre_checkout(
    pre_checkout_query: PreCheckoutQuery,
    config: FromDishka[TelegramConfig],
    profile_service: FromDishka[ProfileServiceProtocol],
) -> None:
    parsed = _parse_payload(pre_checkout_query.invoice_payload, config)
    if parsed is None:
        _ = await pre_checkout_query.answer(ok=False, error_message="Некорректный счёт")
        return

    expected_telegram_id, _ = parsed
    if expected_telegram_id != pre_checkout_query.from_user.id:
        _ = await pre_checkout_query.answer(ok=False, error_message="Счёт принадлежит другому пользователю")
        return

    profile = await profile_service.get_profile(pre_checkout_query.from_user.id)
    if _is_premium_active(profile):
        _ = await pre_checkout_query.answer(ok=False, error_message="Premium уже активен, повторная покупка недоступна")
        return

    _ = await pre_checkout_query.answer(ok=True)


@payments_router.message(F.successful_payment)
async def handle_successful_payment(
    message: Message,
    config: FromDishka[TelegramConfig],
    profile_service: FromDishka[ProfileServiceProtocol],
    cache: FromDishka[CacheProtocol],
    event_publisher: FromDishka[EventPublisherProtocol],
) -> None:
    if message.successful_payment is None or message.from_user is None:
        return

    payment = message.successful_payment
    telegram_id = message.from_user.id
    telegram_charge_id = payment.telegram_payment_charge_id
    provider_charge_id = payment.provider_payment_charge_id

    processed_key = f"payment:processed:{telegram_charge_id}"
    already_processed = await cache.get(processed_key, unmarshal_as=int)
    if already_processed is not None:
        _ = await message.answer("Платёж уже обработан ✅")
        return

    parsed = _parse_payload(payment.invoice_payload, config)
    if parsed is None:
        log.warning("successful_payment with invalid payload", telegram_id=telegram_id)
        _ = await message.answer("Оплата получена, но не удалось подтвердить тариф. Обратитесь в поддержку /support")
        return

    payload_telegram_id, duration_days = parsed
    if payload_telegram_id != telegram_id:
        log.warning(
            "successful_payment telegram_id mismatch",
            telegram_id=telegram_id,
            payload_telegram_id=payload_telegram_id,
        )
        _ = await message.answer("Оплата получена, но идентификатор пользователя не совпал. Обратитесь в /support")
        return

    duration_seconds = duration_days * 24 * 60 * 60
    profile = await profile_service.get_profile(telegram_id)
    if _is_premium_active(profile):
        await cache.set(processed_key, 1, ttl=timedelta(days=365))
        expiry = _format_expiry(profile)
        _ = await message.answer(
            f"Платёж получен, но Premium уже активен до {expiry}. Продление автоматически не выполнено. Напиши в /support."
        )
        return

    expires_at_seconds = await profile_service.activate_subscription(
        ProfileServiceProtocol.ActivateSubscriptionRequest(
            telegram_id=telegram_id,
            tier=SubscriptionTier.PREMIUM,
            duration_seconds=duration_seconds,
            telegram_payment_charge_id=telegram_charge_id,
            provider_payment_charge_id=provider_charge_id,
            invoice_payload=payment.invoice_payload,
        )
    )

    await cache.delete(f"profile:{telegram_id}")
    await cache.set(processed_key, 1, ttl=timedelta(days=365))

    event = {
        "telegram_id": telegram_id,
        "currency": payment.currency,
        "total_amount": payment.total_amount,
        "invoice_payload": payment.invoice_payload,
        "telegram_payment_charge_id": telegram_charge_id,
        "provider_payment_charge_id": provider_charge_id,
        "subscription_expires_at_seconds": expires_at_seconds,
    }
    await event_publisher.publish("billing.subscription.activated", json.dumps(event).encode())

    expiry = datetime.fromtimestamp(expires_at_seconds, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    _ = await message.answer(f"Оплата прошла успешно ✅\nPremium активирован до {expiry}.")
