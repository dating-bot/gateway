from pydantic import BaseModel, Field


class TelegramConfig(BaseModel):
    token: str = Field(description="Telegram bot token")
    webhook_path: str = Field(default="/webhook", description="Путь для вебхука")
    webhook_secret: str = Field(description="Secret для верификации Telegram webhook")
    webhook_host: str = Field(description="Публичный хост (https://example.com)")
