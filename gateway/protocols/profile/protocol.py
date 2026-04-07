from typing import Protocol

import pydantic


class ProfileServiceProtocol(Protocol):
    class GetProfileResult(pydantic.BaseModel):
        found: bool
        profile_id: int
        name: str
        age: int
        city: str
        bio: str
        latitude: float | None = None
        longitude: float | None = None

    class CreateProfileRequest(pydantic.BaseModel):
        telegram_id: int
        name: str
        age: int
        city: str
        bio: str
        gender: int  # profile_pb2.Gender value
        latitude: float | None = None
        longitude: float | None = None

    class UpdateProfileRequest(pydantic.BaseModel):
        telegram_id: int
        name: str
        age: int
        city: str
        bio: str

    class SetGeoRequest(pydantic.BaseModel):
        telegram_id: int
        latitude: float
        longitude: float

    class UploadPhotoRequest(pydantic.BaseModel):
        telegram_id: int
        data: bytes
        content_type: str

    async def get_profile(self, telegram_id: int) -> "ProfileServiceProtocol.GetProfileResult": ...

    async def create_profile(self, request: "ProfileServiceProtocol.CreateProfileRequest") -> int: ...

    async def update_profile(self, request: "ProfileServiceProtocol.UpdateProfileRequest") -> bool: ...

    async def set_geo(self, request: "ProfileServiceProtocol.SetGeoRequest") -> bool: ...

    async def upload_photo(self, request: "ProfileServiceProtocol.UploadPhotoRequest") -> int: ...
