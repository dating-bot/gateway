from typing import Protocol


class AclCheckerProtocol(Protocol):
    async def check(self, user_id: int, requires: dict[str, object]) -> bool: ...
