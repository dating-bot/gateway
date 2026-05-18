from dataclasses import dataclass
from enum import StrEnum
from typing import final

from gateway.domain.profile import Profile
from gateway.protocols.cache import CacheProtocol
from gateway.protocols.profile import ProfileServiceProtocol

_PAUSED_KEY_PREFIX = "profile:paused:"


class ProfileAccessReason(StrEnum):
    ACTIVE = "active"
    NO_PROFILE = "no_profile"
    PAUSED = "paused"


@dataclass(frozen=True, slots=True)
class ProfileAccessDecision:
    allowed: bool
    reason: ProfileAccessReason
    profile: Profile | None = None


@final
class ProfileAccessGuard:
    @staticmethod
    def paused_message() -> str:
        return "Сейчас вашу анкету проверяет администрация. Пока вы не можете смотреть анкеты и отправлять свою анкету."

    @staticmethod
    async def evaluate(
        *,
        telegram_id: int,
        profile_service: ProfileServiceProtocol,
        cache: CacheProtocol,
        profile: Profile | None = None,
    ) -> ProfileAccessDecision:
        current_profile = profile or await profile_service.get_profile(telegram_id)
        if current_profile is None:
            return ProfileAccessDecision(allowed=False, reason=ProfileAccessReason.NO_PROFILE)

        paused = await cache.get(f"{_PAUSED_KEY_PREFIX}{telegram_id}", unmarshal_as=int)
        if paused is not None:
            return ProfileAccessDecision(allowed=False, reason=ProfileAccessReason.PAUSED, profile=current_profile)

        if not current_profile.is_active:
            return ProfileAccessDecision(allowed=False, reason=ProfileAccessReason.PAUSED, profile=current_profile)

        fresh_profile = await profile_service.get_profile_by_id(current_profile.profile_id)
        if fresh_profile is not None and not fresh_profile.is_active:
            return ProfileAccessDecision(allowed=False, reason=ProfileAccessReason.PAUSED, profile=current_profile)

        return ProfileAccessDecision(allowed=True, reason=ProfileAccessReason.ACTIVE, profile=current_profile)
