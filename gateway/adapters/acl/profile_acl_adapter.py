import time
from typing import final, override

import structlog

from gateway.domain.profile import SubscriptionTier
from gateway.protocols.acl import AclCheckerProtocol
from gateway.protocols.cache import CacheProtocol
from gateway.protocols.profile import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.adapters.ProfileAclAdapter")


@final
class ProfileAclAdapter(AclCheckerProtocol):
    """Проверка ACL: активность профиля, подписка, роль.

    Role пока заглушка (always allow), подписка проверяется по profile-service.
    """

    def __init__(
        self,
        *,
        profile_service: ProfileServiceProtocol,
        cache: CacheProtocol,
    ) -> None:
        self._profile_service = profile_service
        self._cache = cache

    @override
    async def check(self, user_id: int, requires: dict[str, object]) -> bool:  # noqa: C901
        if not requires:
            return True

        profile = None
        if requires.get("active"):
            profile = await self._profile_service.get_profile(user_id)
            if profile is None:
                log.debug("acl denied: no profile", user_id=user_id)
                return False
            paused = await self._cache.get(f"profile:paused:{user_id}", unmarshal_as=int)
            if paused is not None:
                log.info("acl denied: profile paused", user_id=user_id)
                return False

        if "subscription" in requires:
            if profile is None:
                profile = await self._profile_service.get_profile(user_id)
            if profile is None:
                log.debug("acl denied: no profile for subscription", user_id=user_id)
                return False

            required = str(requires["subscription"]).strip().upper()
            if required == "PREMIUM":
                expires_at = profile.subscription_expires_at_seconds or 0
                now = int(time.time())
                if profile.subscription_tier != SubscriptionTier.PREMIUM or expires_at <= now:
                    log.info(
                        "acl denied: premium required",
                        user_id=user_id,
                        tier=profile.subscription_tier.value,
                        expires_at=expires_at,
                        now=now,
                    )
                    return False

        if "role" in requires:
            # role-проверка пока заглушка (always allow)
            log.debug("acl role check — stub, always allow", user_id=user_id)

        return True
