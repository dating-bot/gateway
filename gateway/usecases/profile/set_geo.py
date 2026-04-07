from typing import final

import pydantic
import structlog
from grpclib.const import Status
from grpclib.exceptions import GRPCError

from gateway.protocols.profile.protocol import ProfileServiceProtocol
from gateway.usecases.profile.errors import ProfileNotFoundForMutationError, ProfileServiceTransportError
from gateway.usecases.profile.invalidate_profile import InvalidateProfile

log = structlog.stdlib.get_logger("gateway.usecases.profile.SetGeo")


@final
class SetGeo:
    """Сохранить координаты в profile_service и сбросить кэш профиля."""

    def __init__(
        self,
        *,
        profile_service: ProfileServiceProtocol,
        invalidate_profile: InvalidateProfile,
    ) -> None:
        self._profile_service = profile_service
        self._invalidate_profile = invalidate_profile

    class Request(pydantic.BaseModel):
        telegram_id: int
        latitude: float
        longitude: float

    async def execute(self, request: Request) -> None:
        try:
            _ = await self._profile_service.set_geo(
                ProfileServiceProtocol.SetGeoRequest(
                    telegram_id=request.telegram_id,
                    latitude=request.latitude,
                    longitude=request.longitude,
                ),
            )
        except GRPCError as e:
            if e.status == Status.NOT_FOUND:
                msg = "Profile not found"
                raise ProfileNotFoundForMutationError(msg) from e
            log.warning("set_geo grpc error", status=e.status, message=e.message)
            msg = "Profile service error"
            raise ProfileServiceTransportError(msg) from e

        await self._invalidate_profile.execute(InvalidateProfile.Request(telegram_id=request.telegram_id))
