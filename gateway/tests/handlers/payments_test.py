# ruff: noqa: INP001

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gateway.app.telegram.handlers.payments import (
    handle_pre_checkout,
    handle_subscribe,
    handle_subscribe_provider,
    handle_subscribe_stars,
    handle_successful_payment,
)
from gateway.domain.profile import Gender, Profile, SubscriptionTier
from gateway.domain.resolved_callback import ResolvedCallback
from gateway.infra.telegram import TelegramConfig


def _config(**overrides: object) -> TelegramConfig:
    base = {
        "token": "test-token",
        "payment_mode": "stars",
        "subscription_payload_prefix": "premium_30d",
        "subscription_duration_days": 30,
        "subscription_title": "Premium",
        "subscription_description": "Premium access",
        "stars_amount": 100,
        "provider_currency": "RUB",
        "provider_amount": 49900,
    }
    base.update(overrides)
    return TelegramConfig(**base)


def _profile(telegram_id: int, *, premium: bool) -> Profile:
    return Profile(
        telegram_id=telegram_id,
        profile_id=telegram_id,
        name="User",
        age=25,
        city="Moscow",
        bio="Bio",
        gender=Gender.FEMALE,
        photos=[],
        subscription_tier=SubscriptionTier.PREMIUM if premium else SubscriptionTier.FREE,
        subscription_expires_at_seconds=2_200_000_000 if premium else None,
    )


@pytest.mark.asyncio
async def test_handle_subscribe_shows_two_payment_buttons() -> None:
    bot = AsyncMock()
    message = SimpleNamespace(answer=AsyncMock())
    query = SimpleNamespace(
        from_user=SimpleNamespace(id=123),
        message=message,
        bot=bot,
        answer=AsyncMock(),
    )

    get_profile = AsyncMock()
    get_profile.execute.return_value = _profile(123, premium=False)

    await handle_subscribe(
        query,
        ResolvedCallback(handler_id="handle_subscribe", path_params={}),
        get_profile,
        _config(payment_mode="stars"),
    )

    message.answer.assert_awaited_once()
    reply_markup = message.answer.await_args.kwargs["reply_markup"]
    callbacks = [btn.callback_data for row in reply_markup.inline_keyboard for btn in row]
    assert "billing:subscribe:stars" in callbacks
    assert "billing:subscribe:provider" in callbacks
    query.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_subscribe_stars_sends_stars_invoice() -> None:
    bot = AsyncMock()
    query = SimpleNamespace(
        from_user=SimpleNamespace(id=123),
        message=SimpleNamespace(),
        bot=bot,
        answer=AsyncMock(),
    )

    get_profile = AsyncMock()
    get_profile.execute.return_value = _profile(123, premium=False)

    await handle_subscribe_stars(
        query,
        ResolvedCallback(handler_id="handle_subscribe_stars", path_params={}),
        get_profile,
        _config(),
    )

    bot.send_invoice.assert_awaited_once()
    kwargs = bot.send_invoice.await_args.kwargs
    assert kwargs["chat_id"] == 123
    assert kwargs["currency"] == "XTR"
    assert kwargs["provider_token"] == ""
    query.answer.assert_awaited_once_with("Счёт отправлен")


@pytest.mark.asyncio
async def test_handle_subscribe_provider_sends_provider_invoice() -> None:
    bot = AsyncMock()
    query = SimpleNamespace(
        from_user=SimpleNamespace(id=123),
        message=SimpleNamespace(),
        bot=bot,
        answer=AsyncMock(),
    )

    get_profile = AsyncMock()
    get_profile.execute.return_value = _profile(123, premium=False)

    await handle_subscribe_provider(
        query,
        ResolvedCallback(handler_id="handle_subscribe_provider", path_params={}),
        get_profile,
        _config(provider_token="123:TEST:token"),
    )

    bot.send_invoice.assert_awaited_once()
    kwargs = bot.send_invoice.await_args.kwargs
    assert kwargs["currency"] == "RUB"
    assert kwargs["provider_token"] == "123:TEST:token"
    query.answer.assert_awaited_once_with("Счёт отправлен")


@pytest.mark.asyncio
async def test_handle_pre_checkout_rejects_invalid_payload() -> None:
    pre_checkout_query = SimpleNamespace(
        invoice_payload="invalid",
        from_user=SimpleNamespace(id=42),
        answer=AsyncMock(),
    )

    profile_service = AsyncMock()
    await handle_pre_checkout(pre_checkout_query, _config(), profile_service)

    pre_checkout_query.answer.assert_awaited_once_with(ok=False, error_message="Некорректный счёт")


@pytest.mark.asyncio
async def test_handle_successful_payment_activates_subscription_once() -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=77),
        successful_payment=SimpleNamespace(
            telegram_payment_charge_id="tg-charge-1",
            provider_payment_charge_id="pr-charge-1",
            invoice_payload="premium_30d:77:30:1710000000",
            currency="XTR",
            total_amount=100,
        ),
        answer=AsyncMock(),
    )

    cache = AsyncMock()
    cache.get.return_value = None
    profile_service = AsyncMock()
    profile_service.get_profile.return_value = _profile(77, premium=False)
    profile_service.activate_subscription.return_value = 1_800_000_000
    event_publisher = AsyncMock()

    await handle_successful_payment(message, _config(), profile_service, cache, event_publisher)

    profile_service.activate_subscription.assert_awaited_once()
    cache.set.assert_awaited_once()
    event_publisher.publish.assert_awaited_once()
    message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_successful_payment_skips_duplicate_charge() -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=77),
        successful_payment=SimpleNamespace(
            telegram_payment_charge_id="tg-charge-dup",
            provider_payment_charge_id="",
            invoice_payload="premium_30d:77:30:1710000000",
            currency="XTR",
            total_amount=100,
        ),
        answer=AsyncMock(),
    )

    cache = AsyncMock()
    cache.get.return_value = 1
    profile_service = AsyncMock()
    event_publisher = AsyncMock()

    await handle_successful_payment(message, _config(), profile_service, cache, event_publisher)

    profile_service.activate_subscription.assert_not_awaited()
    event_publisher.publish.assert_not_awaited()
    message.answer.assert_awaited_once_with("Платёж уже обработан ✅")


@pytest.mark.asyncio
async def test_handle_subscribe_rejects_when_premium_active() -> None:
    bot = AsyncMock()
    message = SimpleNamespace(answer=AsyncMock())
    query = SimpleNamespace(
        from_user=SimpleNamespace(id=123),
        message=message,
        bot=bot,
        answer=AsyncMock(),
    )
    get_profile = AsyncMock()
    get_profile.execute.return_value = _profile(123, premium=True)

    await handle_subscribe(
        query,
        ResolvedCallback(handler_id="handle_subscribe", path_params={}),
        get_profile,
        _config(),
    )

    query.answer.assert_awaited_once_with("Premium уже активен")
    message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_pre_checkout_rejects_when_premium_active() -> None:
    pre_checkout_query = SimpleNamespace(
        invoice_payload="premium_30d:42:30:1710000000",
        from_user=SimpleNamespace(id=42),
        answer=AsyncMock(),
    )
    profile_service = AsyncMock()
    profile_service.get_profile.return_value = _profile(42, premium=True)

    await handle_pre_checkout(pre_checkout_query, _config(), profile_service)

    pre_checkout_query.answer.assert_awaited_once_with(
        ok=False,
        error_message="Premium уже активен, повторная покупка недоступна",
    )
