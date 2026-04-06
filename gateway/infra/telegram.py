from pydantic import BaseModel, Field

# Valid-format placeholder when token is unset (dev/tests only). Not a secret.
_DEV_BOT_TOKEN_PLACEHOLDER = "1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"  # noqa: S105


class TelegramBotConfig(BaseModel):
    bot_token: str = Field(
        default="",
        description="Telegram bot token from @BotFather; empty uses dev placeholder (not for production)",
    )
    webhook_path: str = Field(default="/webhook", description="POST path for Telegram webhook")
    webhook_secret_token: str | None = Field(
        default=None,
        description="Optional secret for X-Telegram-Bot-Api-Secret-Token (setWebhook)",
    )

    def effective_bot_token(self) -> str:
        t = self.bot_token.strip()
        return t or _DEV_BOT_TOKEN_PLACEHOLDER

    def is_using_placeholder_token(self) -> bool:
        return not self.bot_token.strip()
