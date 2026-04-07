from dataclasses import dataclass
from typing import cast, final, override

from external_clients.profile_api.v1.profile_grpc import ProfileServiceStub
from external_clients.profile_api.v1.profile_pb2 import (
    CreateProfileRequest,
    Gender,
    GetProfileRequest,
    SetGeoRequest,
    UpdateProfileRequest,
    UploadPhotoRequest,
)
from gateway.protocols.profile.protocol import ProfileServiceProtocol


@final
@dataclass(slots=True)
class ProfileServiceClientAdapter(ProfileServiceProtocol):
    _stub: ProfileServiceStub

    @override
    async def get_profile(self, telegram_id: int) -> ProfileServiceProtocol.GetProfileResult:
        response = await self._stub.GetProfile(GetProfileRequest(telegram_id=telegram_id))
        lat = response.latitude if response.HasField("latitude") else None
        lon = response.longitude if response.HasField("longitude") else None
        return ProfileServiceProtocol.GetProfileResult(
            found=response.found,
            profile_id=response.profile_id,
            name=response.name,
            age=response.age,
            city=response.city,
            bio=response.bio,
            latitude=lat,
            longitude=lon,
        )

    @override
    async def create_profile(self, request: ProfileServiceProtocol.CreateProfileRequest) -> int:
        req = CreateProfileRequest(
            telegram_id=request.telegram_id,
            name=request.name,
            age=request.age,
            city=request.city,
            bio=request.bio,
            gender=cast("Gender.ValueType", request.gender),
        )
        if request.latitude is not None:
            req.latitude = request.latitude
        if request.longitude is not None:
            req.longitude = request.longitude
        response = await self._stub.CreateProfile(req)
        return response.profile_id

    @override
    async def update_profile(self, request: ProfileServiceProtocol.UpdateProfileRequest) -> bool:
        response = await self._stub.UpdateProfile(
            UpdateProfileRequest(
                telegram_id=request.telegram_id,
                name=request.name,
                age=request.age,
                city=request.city,
                bio=request.bio,
            )
        )
        return response.success

    @override
    async def set_geo(self, request: ProfileServiceProtocol.SetGeoRequest) -> bool:
        response = await self._stub.SetGeo(
            SetGeoRequest(
                telegram_id=request.telegram_id,
                latitude=request.latitude,
                longitude=request.longitude,
            )
        )
        return response.success

    @override
    async def upload_photo(self, request: ProfileServiceProtocol.UploadPhotoRequest) -> int:
        response = await self._stub.UploadPhoto(
            UploadPhotoRequest(
                telegram_id=request.telegram_id,
                data=request.data,
                content_type=request.content_type,
            )
        )
        return response.photo_id
