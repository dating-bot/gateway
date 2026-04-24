import asyncio
from typing import final

import pydantic
import structlog

from gateway.protocols.match_service import MatchServiceProtocol
from gateway.protocols.profile import ProfileServiceProtocol
from gateway.protocols.ranking_service import RankingServiceProtocol

log = structlog.stdlib.get_logger("gateway.usecases.dating.CheckDatingStatus")


@final
class CheckDatingStatus:
    def __init__(
        self,
        *,
        match_service: MatchServiceProtocol,
        profile_service: ProfileServiceProtocol,
        ranking_service: RankingServiceProtocol,
    ) -> None:
        self._match_service = match_service
        self._profile_service = profile_service
        self._ranking_service = ranking_service

    class Request(pydantic.BaseModel):
        """Current user's Telegram id."""

        telegram_id: int

    class Response(pydantic.BaseModel):
        text: str

    async def execute(self, request: Request) -> Response:
        """Load queue snapshot and last match (diagnostics, no queue side effects)."""
        q_task = asyncio.create_task(
            self._ranking_service.get_viewer_queue_state(request.telegram_id)
        )
        m_task = asyncio.create_task(
            self._match_service.list_user_matches(request.telegram_id, limit=1)
        )
        q_state, matches = await asyncio.gather(q_task, m_task)

        lines: list[str] = ["<b>Диагностика: лента и мэтчи</b>"]
        if q_state is None:
            lines.append("\nОчередь: <i>не удалось получить (см. логи)</i>")
        else:
            q_len, head, preview = q_state
            head_s = str(head) if head else "—"
            prev_s = ", ".join(str(x) for x in preview) if preview else "—"
            lines.append(
                f"\nОчередь: длина <code>{q_len}</code>\n"
                f"След. в очереди (без pop): <code>{head_s}</code>\n"
                f"Превью (до 5): <code>{prev_s}</code>"
            )

        if matches:
            _, other_telegram_id = matches[0]
            other_profile = await self._profile_service.get_profile(other_telegram_id)
            other_name = other_profile.name if other_profile is not None else f"id {other_telegram_id}"
            lines.append(f"\nПоследний мэтч: <b>{other_name}</b>")
        else:
            lines.append("\nПоследний мэтч: <i>пока нет</i>")

        return CheckDatingStatus.Response(text="\n".join(lines))
