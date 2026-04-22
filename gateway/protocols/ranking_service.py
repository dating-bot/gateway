from typing import Protocol


class RankingServiceProtocol(Protocol):
    async def get_next_candidate(self, viewer_id: int) -> tuple[int, int] | None:
        """Returns (profile_id, queue_len) or None if no candidates."""
        ...
