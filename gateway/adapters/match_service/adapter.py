from typing import final, override

import structlog
import structlog.contextvars

from external_clients.match_api.v1.match_grpc import MatchServiceStub
from external_clients.match_api.v1.match_pb2 import (
    HandleLikeRequest,
    HandleSkipRequest,
    ListUserMatchesRequest,
)
from gateway.infra.tracing import current_trace_id, inject_grpc_metadata
from gateway.protocols.match_service import MatchServiceProtocol

log = structlog.stdlib.get_logger("gateway.adapters.MatchServiceAdapter")


@final
class MatchServiceAdapter(MatchServiceProtocol):
    def __init__(self, *, stub: MatchServiceStub) -> None:
        self._stub = stub

    def _grpc_metadata(self) -> list[tuple[str, str]] | None:
        trace_id = str(structlog.contextvars.get_contextvars().get("trace_id") or current_trace_id() or "")
        return inject_grpc_metadata([("trace_id", trace_id)] if trace_id else None)

    @override
    async def handle_like(self, liker_id: int, liked_id: int) -> tuple[bool, int | None]:
        resp = await self._stub.HandleLike(
            HandleLikeRequest(liker_id=liker_id, liked_id=liked_id),
            metadata=self._grpc_metadata(),
        )
        match_id = resp.match_id if resp.HasField("match_id") else None
        return resp.matched, match_id

    @override
    async def handle_skip(self, actor_id: int, target_id: int) -> bool:
        resp = await self._stub.HandleSkip(
            HandleSkipRequest(actor_id=actor_id, target_id=target_id),
            metadata=self._grpc_metadata(),
        )
        return resp.success

    @override
    async def list_user_matches(self, telegram_id: int, *, limit: int = 20) -> list[tuple[int, int]]:
        resp = await self._stub.ListUserMatches(
            ListUserMatchesRequest(telegram_id=telegram_id, limit=limit),
            metadata=self._grpc_metadata(),
        )
        return [(m.match_id, m.other_telegram_id) for m in resp.matches]
