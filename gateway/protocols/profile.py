from dataclasses import dataclass
from typing import Protocol

from gateway.domain.profile import Gender, Profile, SubscriptionTier


class ProfileServiceProtocol(Protocol):
    @dataclass
    class Preferences:
        gender_pref: Gender
        age_min: int
        age_max: int
        max_distance_km: int

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
    async def get_preferences(self, telegram_id: int) -> "ProfileServiceProtocol.Preferences | None": ...

    @dataclass
    class ActivateSubscriptionRequest:
        telegram_id: int
        tier: SubscriptionTier
        duration_seconds: int
        telegram_payment_charge_id: str | None = None
        provider_payment_charge_id: str | None = None
        invoice_payload: str | None = None

    async def activate_subscription(self, request: "ProfileServiceProtocol.ActivateSubscriptionRequest") -> int: ...
