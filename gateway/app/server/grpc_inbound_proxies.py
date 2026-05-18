from dataclasses import dataclass
from typing import Any, final, override

import structlog
import structlog.contextvars
from google.protobuf.message import Message
from grpclib.const import Status
from grpclib.exceptions import GRPCError

import external_clients.match_api.v1.match_pb2 as match_in_pb2
import external_clients.ranking_api.v1.ranking_pb2 as ranking_in_pb2
from external_clients.match_api.v1.match_grpc import MatchServiceBase, MatchServiceStub
from external_clients.profile_api.v1.profile_grpc import ProfileServiceBase, ProfileServiceStub
from external_clients.ranking_api.v1.ranking_grpc import RankingServiceBase, RankingServiceStub
from gateway.app.server.utils import unary
from gateway.infra.tracing import current_trace_id, inject_grpc_metadata
from profile_api.v1 import profile_pb2

log = structlog.stdlib.get_logger("gateway.grpc.inbound_proxies")


def _align_for_stub_method(stub_method: object, message: Message) -> Message:
    request_type: type[Message] | None = getattr(stub_method, "request_type", None)
    if request_type is None or isinstance(message, request_type):
        return message
    aligned: Message = request_type()  # type: ignore[assignment]
    aligned.ParseFromString(message.SerializeToString())
    return aligned


def _align_response_for_handler(handler_reply_class: type[Message] | None, response: Message) -> Message:
    if handler_reply_class is None or isinstance(response, handler_reply_class):
        return response
    out: Message = handler_reply_class()  # type: ignore[assignment]
    out.ParseFromString(response.SerializeToString())
    return out


async def _proxy_unary[Resp: Message](
    *, upstream: str, stub_method: Any, request: Message, response_message_cls: type[Resp] | None
) -> Message:
    try:
        req = _align_for_stub_method(stub_method, request)
        trace_id = str(structlog.contextvars.get_contextvars().get("trace_id") or current_trace_id() or "")
        metadata = inject_grpc_metadata([("trace_id", trace_id)] if trace_id else None)
        resp: Message = await stub_method(req, metadata=metadata)
        return _align_response_for_handler(response_message_cls, resp)
    except GRPCError:
        raise
    except (TimeoutError, OSError, ConnectionError) as e:
        log.exception("upstream gRPC network error", upstream=upstream, error=str(e))
        raise GRPCError(
            Status.UNAVAILABLE,
            f"{upstream} unreachable ({type(e).__name__}: {e})",
        ) from e
    except Exception as e:
        log.exception("upstream gRPC call failed", upstream=upstream, error=str(e))
        raise GRPCError(Status.INTERNAL, f"{upstream} error: {e}") from e


@final
@dataclass(slots=True)
class ProfileGrpcInboundProxy(ProfileServiceBase):
    _stub: ProfileServiceStub

    @override
    @unary
    async def Health(self, request: profile_pb2.HealthRequest) -> profile_pb2.HealthResponse:
        return await _proxy_unary(
            upstream="profile-service",
            stub_method=self._stub.Health,
            request=request,
            response_message_cls=profile_pb2.HealthResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def CreateProfile(self, request: profile_pb2.CreateProfileRequest) -> profile_pb2.CreateProfileResponse:
        return await _proxy_unary(
            upstream="profile-service",
            stub_method=self._stub.CreateProfile,
            request=request,
            response_message_cls=profile_pb2.CreateProfileResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def GetProfile(self, request: profile_pb2.GetProfileRequest) -> profile_pb2.GetProfileResponse:
        return await _proxy_unary(
            upstream="profile-service",
            stub_method=self._stub.GetProfile,
            request=request,
            response_message_cls=profile_pb2.GetProfileResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def GetProfileById(self, request: profile_pb2.GetProfileByIdRequest) -> profile_pb2.GetProfileByIdResponse:
        return await _proxy_unary(
            upstream="profile-service",
            stub_method=self._stub.GetProfileById,
            request=request,
            response_message_cls=profile_pb2.GetProfileByIdResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def UpdateProfile(self, request: profile_pb2.UpdateProfileRequest) -> profile_pb2.UpdateProfileResponse:
        return await _proxy_unary(
            upstream="profile-service",
            stub_method=self._stub.UpdateProfile,
            request=request,
            response_message_cls=profile_pb2.UpdateProfileResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def SetGeo(self, request: profile_pb2.SetGeoRequest) -> profile_pb2.SetGeoResponse:
        return await _proxy_unary(
            upstream="profile-service",
            stub_method=self._stub.SetGeo,
            request=request,
            response_message_cls=profile_pb2.SetGeoResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def UploadPhoto(self, request: profile_pb2.UploadPhotoRequest) -> profile_pb2.UploadPhotoResponse:
        return await _proxy_unary(
            upstream="profile-service",
            stub_method=self._stub.UploadPhoto,
            request=request,
            response_message_cls=profile_pb2.UploadPhotoResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def DeletePhoto(self, request: profile_pb2.DeletePhotoRequest) -> profile_pb2.DeletePhotoResponse:
        return await _proxy_unary(
            upstream="profile-service",
            stub_method=self._stub.DeletePhoto,
            request=request,
            response_message_cls=profile_pb2.DeletePhotoResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def GetPresignedUrl(self, request: profile_pb2.GetPresignedUrlRequest) -> profile_pb2.GetPresignedUrlResponse:
        return await _proxy_unary(
            upstream="profile-service",
            stub_method=self._stub.GetPresignedUrl,
            request=request,
            response_message_cls=profile_pb2.GetPresignedUrlResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def SetPreferences(self, request: profile_pb2.SetPreferencesRequest) -> profile_pb2.SetPreferencesResponse:
        return await _proxy_unary(
            upstream="profile-service",
            stub_method=self._stub.SetPreferences,
            request=request,
            response_message_cls=profile_pb2.SetPreferencesResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def GetPreferences(self, request: profile_pb2.GetPreferencesRequest) -> profile_pb2.GetPreferencesResponse:
        return await _proxy_unary(
            upstream="profile-service",
            stub_method=self._stub.GetPreferences,
            request=request,
            response_message_cls=profile_pb2.GetPreferencesResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def ActivateSubscription(
        self, request: profile_pb2.ActivateSubscriptionRequest
    ) -> profile_pb2.ActivateSubscriptionResponse:
        return await _proxy_unary(
            upstream="profile-service",
            stub_method=self._stub.ActivateSubscription,
            request=request,
            response_message_cls=profile_pb2.ActivateSubscriptionResponse,
        )  # type: ignore[return-value]


@final
@dataclass(slots=True)
class RankingGrpcInboundProxy(RankingServiceBase):
    _stub: RankingServiceStub

    @override
    @unary
    async def GetNextCandidate(
        self, request: ranking_in_pb2.GetNextCandidateRequest
    ) -> ranking_in_pb2.GetNextCandidateResponse:
        return await _proxy_unary(
            upstream="ranking-service",
            stub_method=self._stub.GetNextCandidate,
            request=request,
            response_message_cls=ranking_in_pb2.GetNextCandidateResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def UpdateEngagement(
        self, request: ranking_in_pb2.UpdateEngagementRequest
    ) -> ranking_in_pb2.UpdateEngagementResponse:
        return await _proxy_unary(
            upstream="ranking-service",
            stub_method=self._stub.UpdateEngagement,
            request=request,
            response_message_cls=ranking_in_pb2.UpdateEngagementResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def GetViewerQueueState(
        self, request: ranking_in_pb2.GetViewerQueueStateRequest
    ) -> ranking_in_pb2.GetViewerQueueStateResponse:
        return await _proxy_unary(
            upstream="ranking-service",
            stub_method=self._stub.GetViewerQueueState,
            request=request,
            response_message_cls=ranking_in_pb2.GetViewerQueueStateResponse,
        )  # type: ignore[return-value]


@final
@dataclass(slots=True)
class MatchGrpcInboundProxy(MatchServiceBase):
    _stub: MatchServiceStub

    @override
    @unary
    async def Health(self, request: match_in_pb2.HealthRequest) -> match_in_pb2.HealthResponse:
        return await _proxy_unary(
            upstream="match-service",
            stub_method=self._stub.Health,
            request=request,
            response_message_cls=match_in_pb2.HealthResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def HandleLike(self, request: match_in_pb2.HandleLikeRequest) -> match_in_pb2.HandleLikeResponse:
        return await _proxy_unary(
            upstream="match-service",
            stub_method=self._stub.HandleLike,
            request=request,
            response_message_cls=match_in_pb2.HandleLikeResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def HandleSkip(self, request: match_in_pb2.HandleSkipRequest) -> match_in_pb2.HandleSkipResponse:
        return await _proxy_unary(
            upstream="match-service",
            stub_method=self._stub.HandleSkip,
            request=request,
            response_message_cls=match_in_pb2.HandleSkipResponse,
        )  # type: ignore[return-value]

    @override
    @unary
    async def ListUserMatches(
        self, request: match_in_pb2.ListUserMatchesRequest
    ) -> match_in_pb2.ListUserMatchesResponse:
        return await _proxy_unary(
            upstream="match-service",
            stub_method=self._stub.ListUserMatches,
            request=request,
            response_message_cls=match_in_pb2.ListUserMatchesResponse,
        )  # type: ignore[return-value]
