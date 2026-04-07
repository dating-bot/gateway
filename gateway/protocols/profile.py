from dataclasses import dataclass
from typing import Protocol

from gateway.domain.profile import Gender, Profile


class ProfileServiceProtocol(Protocol):
    """Порт для работы с profile-service."""

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

    async def create_profile(self, request: "ProfileServiceProtocol.CreateRequest") -> int:
        """Возвращает profile_id."""
        ...

    async def update_profile(self, request: "ProfileServiceProtocol.UpdateRequest") -> None: ...

    async def set_geo(self, telegram_id: int, latitude: float, longitude: float) -> None: ...

    async def upload_photo(self, telegram_id: int, data: bytes, content_type: str) -> int:
        """Возвращает photo_id."""
        ...

    async def get_presigned_url(self, photo_id: int) -> str: ...
