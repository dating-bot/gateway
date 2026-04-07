from typing import final

import structlog

from gateway.protocols.cache.protocol import CacheProtocol
from gateway.protocols.profile.protocol import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.adapters.acl.ProfileAclAdapter")


@final
class ProfileAclAdapter:
    def __init__(
        self,
        *,
        profile_service: ProfileServiceProtocol,
        cache: CacheProtocol,
    ) -> None:
        self._profile_service = profile_service
        self._cache = cache

    async def check(self, user_id: int, requires: dict[str, object]) -> bool:
        if requires.get("active"):
            result = await self._get_profile(user_id=user_id)
            if not result.found:
                log.debug("acl_denied_no_profile", user_id=user_id)
                return False

        # subscription и role — заглушка до подключения billing/admin
        if "subscription" in requires or "role" in requires:
            log.debug("acl_stub_allow_subscription_role", user_id=user_id, requires=requires)

        return True

    async def _get_profile(
        self,
        user_id: int,
    ) -> ProfileServiceProtocol.GetProfileResult:
        key = f"profile:{user_id}"
        cached = await self._cache.get(key, unmarshal_as=ProfileServiceProtocol.GetProfileResult)
        if cached is not None:
            return cached
        result = await self._profile_service.get_profile(user_id)
        if result.found:
            await self._cache.set(key, result)
        return result
