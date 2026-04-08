from pydantic import BaseModel, Field


class TelegramConfig(BaseModel):
    token: str = Field(description="Telegram bot token")
    webhook_path: str = Field(default="/webhook", description="Путь для вебхука")
    webhook_secret: str | None = Field(default=None, description="Secret для верификации Telegram webhook; если не задан — проверка токена отключена")
    webhook_host: str | None = Field(default=None, description="Публичный хост (https://example.com); если не задан — webhook не регистрируется")
