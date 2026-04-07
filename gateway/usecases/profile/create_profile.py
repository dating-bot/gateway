from typing import final

import pydantic
import structlog
from grpclib.const import Status
from grpclib.exceptions import GRPCError

from gateway.protocols.profile.protocol import ProfileServiceProtocol
from gateway.usecases.profile.errors import DuplicateProfileError, ProfileServiceTransportError
from gateway.usecases.profile.get_profile import GetProfile

log = structlog.stdlib.get_logger("gateway.usecases.profile.CreateProfile")


@final
class CreateProfile:
    """Create profile via gRPC, then refresh cache via GetProfile."""

    def __init__(
        self,
        *,
        profile_service: ProfileServiceProtocol,
        get_profile: GetProfile,
    ) -> None:
        self._profile_service = profile_service
        self._get_profile = get_profile

    class Request(pydantic.BaseModel):
        telegram_id: int
        name: str
        age: int
        city: str
        bio: str
        gender: int  # profile_pb2.Gender value (MALE / FEMALE)
        latitude: float | None = None
        longitude: float | None = None

    class Response(pydantic.BaseModel):
        profile: ProfileServiceProtocol.GetProfileResult

    async def execute(self, request: Request) -> Response:
        try:
            _ = await self._profile_service.create_profile(
                ProfileServiceProtocol.CreateProfileRequest(
                    telegram_id=request.telegram_id,
                    name=request.name,
                    age=request.age,
                    city=request.city,
                    bio=request.bio,
                    gender=request.gender,
                    latitude=request.latitude,
                    longitude=request.longitude,
                ),
            )
        except GRPCError as e:
            if e.status == Status.ALREADY_EXISTS:
                msg = "Profile already exists"
                raise DuplicateProfileError(msg) from e
            log.warning("create_profile grpc error", status=e.status, message=e.message)
            msg = "Profile service error"
            raise ProfileServiceTransportError(msg) from e

        refreshed = await self._get_profile.execute(GetProfile.Request(telegram_id=request.telegram_id))
        if refreshed.profile is None:
            log.error("profile missing after create", telegram_id=request.telegram_id)
            msg = "Profile missing after create"
            raise ProfileServiceTransportError(msg)

        return self.Response(profile=refreshed.profile)
