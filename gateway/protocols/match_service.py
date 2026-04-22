from typing import Protocol


class MatchServiceProtocol(Protocol):
    async def handle_like(self, liker_id: int, liked_id: int) -> tuple[bool, int | None]:
        """Returns (matched, match_id)."""
        ...

    async def handle_skip(self, actor_id: int, target_id: int) -> bool:
        """Returns success."""
        ...
