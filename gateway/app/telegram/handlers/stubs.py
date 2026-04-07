from aiogram.types import CallbackQuery

from gateway.domain.resolved_callback import ResolvedCallback

_STUB_ANSWERS: dict[str, str] = {
    "handle_like": "❤️",
    "handle_skip": "👎",
    "handle_undo": "↩️",
    "handle_super_like": "⭐",
    "handle_settings": "⚙️ Настройки — скоро",
    "handle_subscribe": "💎 Подписка — скоро",
    "handle_boost": "🚀 Буст — скоро",
    "handle_cancel_sub": "❌ Отмена подписки — скоро",
    "handle_ban": "🔨 Забанен",
    "handle_unban": "✅ Разбанен",
}


async def handle_stub(query: CallbackQuery, resolved: ResolvedCallback) -> None:
    answer = _STUB_ANSWERS.get(resolved.handler_id, "🔧 В разработке")
    _ = await query.answer(answer)
