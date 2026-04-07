from typing import final

import pydantic
import structlog
from grpclib.const import Status
from grpclib.exceptions import GRPCError

from gateway.protocols.profile.protocol import ProfileServiceProtocol
from gateway.usecases.profile.errors import ProfileNotFoundForMutationError, ProfileServiceTransportError
from gateway.usecases.profile.get_profile import GetProfile
from gateway.usecases.profile.invalidate_profile import InvalidateProfile

log = structlog.stdlib.get_logger("gateway.usecases.profile.UpdateProfile")


@final
class UpdateProfile:
    """Update profile via gRPC, invalidate cache, reload via GetProfile."""

    def __init__(
        self,
        *,
        profile_service: ProfileServiceProtocol,
        invalidate_profile: InvalidateProfile,
        get_profile: GetProfile,
    ) -> None:
        self._profile_service = profile_service
        self._invalidate_profile = invalidate_profile
        self._get_profile = get_profile

    class Request(pydantic.BaseModel):
        telegram_id: int
        name: str
        age: int
        city: str
        bio: str

    class Response(pydantic.BaseModel):
        profile: ProfileServiceProtocol.GetProfileResult

    async def execute(self, request: Request) -> Response:
        try:
            _ = await self._profile_service.update_profile(
                ProfileServiceProtocol.UpdateProfileRequest(
                    telegram_id=request.telegram_id,
                    name=request.name,
                    age=request.age,
                    city=request.city,
                    bio=request.bio,
                ),
            )
        except GRPCError as e:
            if e.status == Status.NOT_FOUND:
                msg = "Profile not found"
                raise ProfileNotFoundForMutationError(msg) from e
            log.warning("update_profile grpc error", status=e.status, message=e.message)
            msg = "Profile service error"
            raise ProfileServiceTransportError(msg) from e

        await self._invalidate_profile.execute(InvalidateProfile.Request(telegram_id=request.telegram_id))
        refreshed = await self._get_profile.execute(GetProfile.Request(telegram_id=request.telegram_id))
        if refreshed.profile is None:
            log.error("profile missing after update", telegram_id=request.telegram_id)
            msg = "Profile missing after update"
            raise ProfileServiceTransportError(msg)

        return self.Response(profile=refreshed.profile)
