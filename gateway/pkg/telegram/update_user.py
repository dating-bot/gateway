from typing import cast

from aiogram.types import Update, User

# Update types where the initiating user is stored in .from_user
_FROM_USER_ATTRS: frozenset[str] = frozenset({
    "message",
    "edited_message",
    "channel_post",
    "edited_channel_post",
    "business_message",
    "edited_business_message",
    "callback_query",
    "inline_query",
    "chosen_inline_result",
    "shipping_query",
    "pre_checkout_query",
    "purchased_paid_media",
    "my_chat_member",
    "chat_member",
    "chat_join_request",
})

# Update types where the initiating user is stored in .user (not .from_user)
_USER_ATTRS: frozenset[str] = frozenset({
    "message_reaction",
    "business_connection",
    "managed_bot",
})


def _get_update_part(update: Update, attr: str) -> object | None:
    return cast("object | None", getattr(update, attr, None))


def user_id_from_update(update: Update) -> int | None:
    for attr in _FROM_USER_ATTRS:
        obj = _get_update_part(update, attr)
        if obj is None:
            continue
        fu = cast("object | None", getattr(obj, "from_user", None))
        if isinstance(fu, User):
            return fu.id

    for attr in _USER_ATTRS:
        obj = _get_update_part(update, attr)
        if obj is None:
            continue
        u = cast("object | None", getattr(obj, "user", None))
        if isinstance(u, User):
            return u.id

    pa = update.poll_answer
    if pa and pa.user:
        return pa.user.id

    return None
