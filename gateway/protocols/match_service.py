from typing import Protocol


class MatchServiceProtocol(Protocol):
    async def handle_like(self, liker_id: int, liked_id: int) -> tuple[bool, int | None]:
        """Returns (matched, match_id)."""
        ...

    async def handle_skip(self, actor_id: int, target_id: int) -> bool:
        """Returns success."""
        ...

    async def list_user_matches(self, telegram_id: int, *, limit: int = 20) -> list[tuple[int, int]]:
        """Returns (match_id, other_telegram_id) for recent matches."""
        ...
