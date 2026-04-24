from typing import final, override

import structlog

from external_clients.match_api.v1.match_grpc import MatchServiceStub
from external_clients.match_api.v1.match_pb2 import (
    HandleLikeRequest,
    HandleSkipRequest,
    ListUserMatchesRequest,
)
from gateway.protocols.match_service import MatchServiceProtocol

log = structlog.stdlib.get_logger("gateway.adapters.MatchServiceAdapter")


@final
class MatchServiceAdapter(MatchServiceProtocol):
    def __init__(self, *, stub: MatchServiceStub) -> None:
        self._stub = stub

    @override
    async def handle_like(self, liker_id: int, liked_id: int) -> tuple[bool, int | None]:
        resp = await self._stub.HandleLike(HandleLikeRequest(liker_id=liker_id, liked_id=liked_id))
        match_id = resp.match_id if resp.HasField("match_id") else None
        return resp.matched, match_id

    @override
    async def handle_skip(self, actor_id: int, target_id: int) -> bool:
        resp = await self._stub.HandleSkip(HandleSkipRequest(actor_id=actor_id, target_id=target_id))
        return resp.success

    @override
    async def list_user_matches(self, telegram_id: int, *, limit: int = 20) -> list[tuple[int, int]]:
        resp = await self._stub.ListUserMatches(
            ListUserMatchesRequest(telegram_id=telegram_id, limit=limit)
        )
        return [(m.match_id, m.other_telegram_id) for m in resp.matches]
