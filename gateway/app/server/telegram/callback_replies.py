"""Stub callback answers keyed by `handler_id` (must match YAML routes).

Replace with usecase calls per handler when business logic grows.
Keeping a single mapping keeps the hot path O(1) and easy to extend.
"""

from typing import Final

# Immutable lookup: add a row when you add a route in routes.yaml.
CALLBACK_STUB_ANSWER: Final[dict[str, str]] = {
    "handle_like": "❤️",
    "handle_skip": "👎",
    "handle_undo": "↩️",
    "handle_super_like": "⭐",
    "handle_profile_edit": "✏️",
    "handle_profile_view": "👤",
    "handle_settings": "⚙️",
    "handle_subscribe": "💳",
    "handle_boost": "🚀",
    "handle_cancel_sub": "❌",
    "handle_ban": "🔨",
    "handle_unban": "✅",
}
