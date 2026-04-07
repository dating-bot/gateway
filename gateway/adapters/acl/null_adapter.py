from typing import final

import structlog

log = structlog.stdlib.get_logger("gateway.adapters.acl.NullAclAdapter")


@final
class NullAclAdapter:
    """Заглушка ACL — разрешает все действия всем пользователям.

    Используется до подключения реального profile/billing сервиса.
    Заменить на реальный адаптер, когда появится profile-service.
    """

    async def check(self, user_id: int, requires: dict[str, object]) -> bool:
        log.debug("acl_stub_allow_all", user_id=user_id, requires=requires)
        return True
