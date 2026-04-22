from typing import final, override

import structlog

from external_clients.ranking_api.v1.ranking_grpc import RankingServiceStub
from external_clients.ranking_api.v1.ranking_pb2 import GetNextCandidateRequest
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
            return (resp.profile_id, resp.queue_len)
        except Exception:
            log.exception("get_next_candidate failed", viewer_id=viewer_id)
            return None
