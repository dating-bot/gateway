from typing import Protocol


class RankingServiceProtocol(Protocol):
    async def get_next_candidate(self, viewer_id: int) -> tuple[int, int] | None:
        """Returns (profile_id, queue_len) or None if no candidates."""
        ...

    async def get_viewer_queue_state(self, viewer_id: int) -> tuple[int, int, list[int]] | None:
        """Returns (queue_len, head_candidate_telegram_id, preview_ids) or None on error."""
        ...
