from typing import final

import pydantic
import structlog
from grpclib.const import Status
from grpclib.exceptions import GRPCError

from gateway.protocols.profile.protocol import ProfileServiceProtocol
from gateway.usecases.profile.errors import ProfileServiceTransportError
from gateway.usecases.profile.invalidate_profile import InvalidateProfile

log = structlog.stdlib.get_logger("gateway.usecases.profile.UploadProfilePhoto")


@final
class UploadProfilePhoto:
    """UploadPhoto в profile_service + инвалидация кэша профиля."""

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
        data: bytes
        content_type: str

    class Response(pydantic.BaseModel):
        photo_id: int

    async def execute(self, request: Request) -> Response:
        try:
            photo_id = await self._profile_service.upload_photo(
                ProfileServiceProtocol.UploadPhotoRequest(
                    telegram_id=request.telegram_id,
                    data=request.data,
                    content_type=request.content_type,
                ),
            )
        except GRPCError as e:
            if e.status == Status.NOT_FOUND:
                msg = "Profile not found"
                raise ProfileServiceTransportError(msg) from e
            log.warning("upload_photo grpc error", status=e.status, message=e.message)
            msg = "Profile service error"
            raise ProfileServiceTransportError(msg) from e

        await self._invalidate_profile.execute(InvalidateProfile.Request(telegram_id=request.telegram_id))
        return self.Response(photo_id=photo_id)
