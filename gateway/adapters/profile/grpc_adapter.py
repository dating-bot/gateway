from typing import final, override

import structlog

from external_clients.profile_api.v1.profile_grpc import ProfileServiceStub
from external_clients.profile_api.v1.profile_pb2 import (
    CreateProfileRequest,
    Gender,
    GetPresignedUrlRequest,
    GetProfileRequest,
    SetGeoRequest,
    UpdateProfileRequest,
    UploadPhotoRequest,
)
from gateway.domain.profile import Gender as DomainGender
from gateway.domain.profile import PhotoInfo, Profile
from gateway.protocols.profile import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.adapters.GrpcProfileServiceAdapter")

_GENDER_MAP: dict[DomainGender, int] = {
    DomainGender.UNSPECIFIED: Gender.GENDER_UNSPECIFIED,
    DomainGender.MALE: Gender.GENDER_MALE,
    DomainGender.FEMALE: Gender.GENDER_FEMALE,
}

_GENDER_REVERSE: dict[int, DomainGender] = {v: k for k, v in _GENDER_MAP.items()}


@final
class GrpcProfileServiceAdapter(ProfileServiceProtocol):
    def __init__(self, *, stub: ProfileServiceStub) -> None:
        self._stub = stub

    @override
    async def get_profile(self, telegram_id: int) -> Profile | None:
        resp = await self._stub.GetProfile(GetProfileRequest(telegram_id=telegram_id))
        if not resp.found:
            return None
        return Profile(
            telegram_id=telegram_id,
            profile_id=resp.profile_id,
            name=resp.name,
            age=resp.age,
            city=resp.city,
            bio=resp.bio,
            gender=_GENDER_REVERSE.get(resp.gender, DomainGender.UNSPECIFIED),
            photos=[PhotoInfo(photo_id=p.photo_id, is_active=p.is_active) for p in resp.photos],
            latitude=resp.latitude if resp.HasField("latitude") else None,
            longitude=resp.longitude if resp.HasField("longitude") else None,
        )

    @override
    async def create_profile(self, request: ProfileServiceProtocol.CreateRequest) -> int:
        resp = await self._stub.CreateProfile(
            CreateProfileRequest(
                telegram_id=request.telegram_id,
                name=request.name,
                age=request.age,
                city=request.city,
                bio=request.bio,
                gender=_GENDER_MAP.get(request.gender, Gender.GENDER_UNSPECIFIED),
                latitude=request.latitude,
                longitude=request.longitude,
            )
        )
        return resp.profile_id

    @override
    async def update_profile(self, request: ProfileServiceProtocol.UpdateRequest) -> None:
        _ = await self._stub.UpdateProfile(
            UpdateProfileRequest(
                telegram_id=request.telegram_id,
                name=request.name,
                age=request.age,
                city=request.city,
                bio=request.bio,
            )
        )

    @override
    async def set_geo(self, telegram_id: int, latitude: float, longitude: float) -> None:
        _ = await self._stub.SetGeo(SetGeoRequest(telegram_id=telegram_id, latitude=latitude, longitude=longitude))

    @override
    async def upload_photo(self, telegram_id: int, data: bytes, content_type: str) -> int:
        resp = await self._stub.UploadPhoto(
            UploadPhotoRequest(telegram_id=telegram_id, data=data, content_type=content_type)
        )
        return resp.photo_id

    @override
    async def get_presigned_url(self, photo_id: int) -> str:
        resp = await self._stub.GetPresignedUrl(GetPresignedUrlRequest(photo_id=photo_id))
        return resp.url
