from dataclasses import dataclass
from typing import Protocol

from gateway.domain.profile import Gender, Profile


class ProfileServiceProtocol(Protocol):
    @dataclass
    class CreateRequest:
        telegram_id: int
        name: str
        age: int
        city: str
        bio: str
        gender: Gender
        latitude: float | None = None
        longitude: float | None = None

    @dataclass
    class UpdateRequest:
        telegram_id: int
        name: str
        age: int
        city: str
        bio: str

    async def get_profile(self, telegram_id: int) -> Profile | None: ...

    async def get_profile_by_id(self, profile_id: int) -> Profile | None: ...

    async def create_profile(self, request: "ProfileServiceProtocol.CreateRequest") -> int: ...

    async def update_profile(self, request: "ProfileServiceProtocol.UpdateRequest") -> None: ...

    async def set_geo(self, telegram_id: int, latitude: float, longitude: float) -> None: ...

    async def upload_photo(self, telegram_id: int, data: bytes, content_type: str) -> int: ...

    async def delete_photo(self, telegram_id: int, photo_id: int) -> None: ...

    async def get_presigned_url(self, photo_id: int) -> str: ...

    @dataclass
    class SetPreferencesRequest:
        telegram_id: int
        gender_pref: Gender
        age_min: int
        age_max: int
        max_distance_km: int

    async def set_preferences(self, request: "ProfileServiceProtocol.SetPreferencesRequest") -> None: ...
