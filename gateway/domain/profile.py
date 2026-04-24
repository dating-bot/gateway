from dataclasses import dataclass, field
from enum import StrEnum


class Gender(StrEnum):
    ANY = "any"
    UNSPECIFIED = "unspecified"
    MALE = "male"
    FEMALE = "female"


@dataclass(frozen=True, slots=True)
class PhotoInfo:
    photo_id: int
    is_active: bool


@dataclass(frozen=True, slots=True)
class Profile:
    telegram_id: int
    profile_id: int
    name: str
    age: int
    city: str
    bio: str
    gender: Gender
    photos: list[PhotoInfo] = field(default_factory=list)
    latitude: float | None = None
    longitude: float | None = None
