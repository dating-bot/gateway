from typing import final, override

import structlog

from gateway.protocols.acl import AclCheckerProtocol
from gateway.protocols.cache import CacheProtocol
from gateway.protocols.profile import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.adapters.ProfileAclAdapter")


@final
class ProfileAclAdapter(AclCheckerProtocol):
    """Проверка ACL: активность профиля, подписка, роль.

    Subscription и role — заглушки (всегда allow) до появления billing-service.
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
    async def check(self, user_id: int, requires: dict[str, object]) -> bool:
        if not requires:
            return True

        if requires.get("active"):
            profile = await self._profile_service.get_profile(user_id)
            if profile is None:
                log.debug("acl denied: no profile", user_id=user_id)
                return False

        if "subscription" in requires:
            # TODO: проверить тариф через billing-service
            log.debug("acl subscription check — stub, always allow", user_id=user_id)

        if "role" in requires:
            # TODO: проверить роль через admin-service или конфиг
            log.debug("acl role check — stub, always allow", user_id=user_id)

        return True
