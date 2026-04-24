from typing import final, override

import structlog

from external_clients.ranking_api.v1.ranking_grpc import RankingServiceStub
from external_clients.ranking_api.v1.ranking_pb2 import (
    GetNextCandidateRequest,
    GetViewerQueueStateRequest,
)
from gateway.protocols.ranking_service import RankingServiceProtocol

log = structlog.stdlib.get_logger("gateway.adapters.RankingServiceAdapter")


@final
class RankingServiceAdapter(RankingServiceProtocol):
    def __init__(self, *, stub: RankingServiceStub) -> None:
        self._stub = stub

    @override
    async def get_next_candidate(self, viewer_id: int) -> tuple[int, int] | None:
        try:
            resp = await self._stub.GetNextCandidate(GetNextCandidateRequest(viewer_id=viewer_id))
            log.info(
                "get_next_candidate returned",
                viewer_id=viewer_id,
                profile_id=resp.profile_id,
                queue_len=resp.queue_len,
            )
            return (resp.profile_id, resp.queue_len)
        except Exception:
            log.exception("get_next_candidate failed", viewer_id=viewer_id)
            return None

    @override
    async def get_viewer_queue_state(
        self, viewer_id: int
    ) -> tuple[int, int, list[int]] | None:
        try:
            resp = await self._stub.GetViewerQueueState(GetViewerQueueStateRequest(viewer_id=viewer_id))
            return (
                int(resp.queue_len),
                int(resp.head_candidate_telegram_id),
                list(resp.preview_telegram_ids),
            )
        except Exception:
            log.exception("get_viewer_queue_state failed", viewer_id=viewer_id)
            return None
