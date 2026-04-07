from typing import Protocol, runtime_checkable


@runtime_checkable
class AclChecker(Protocol):
    async def check(self, user_id: int, requires: dict[str, object]) -> bool: ...
