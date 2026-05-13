from pydantic import BaseModel, Field


class TelegramConfig(BaseModel):
    token: str = Field(description="Telegram bot token")
    webhook_path: str = Field(default="/webhook", description="Путь для вебхука")
    webhook_secret: str | None = Field(
        default=None, description="Secret для верификации Telegram webhook; если не задан — проверка токена отключена"
    )
    webhook_host: str | None = Field(
        default=None, description="Публичный хост (https://example.com); если не задан — webhook не регистрируется"
    )
    payment_mode: str = Field(
        default="stars",
        description="Режим платежей: stars | provider | auto",
    )
    provider_token: str | None = Field(
        default=None,
        description="Provider token из BotFather для fiat-платежей",
    )
    subscription_title: str = Field(default="Подписка Premium", description="Заголовок invoice")
    subscription_description: str = Field(default="Доступ к премиум-функциям", description="Описание invoice")
    subscription_payload_prefix: str = Field(default="premium_30d", description="Префикс invoice payload")
    subscription_duration_days: int = Field(default=30, description="Срок подписки в днях")
    stars_amount: int = Field(default=100, description="Цена в Telegram Stars (XTR)")
    provider_currency: str = Field(default="RUB", description="Валюта для provider платежей")
    provider_amount: int = Field(default=49900, description="Цена в минимальных единицах валюты (например, копейки)")
    free_like_daily_limit: int = Field(default=50, description="Дневной лимит лайков для free")
    free_super_like_daily_limit: int = Field(default=1, description="Дневной лимит super like для free")
    free_undo_daily_limit: int = Field(default=3, description="Дневной лимит undo для free")
