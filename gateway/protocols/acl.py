from dataclasses import dataclass
from typing import Protocol


class AclCheckerProtocol(Protocol):
    @dataclass(frozen=True, slots=True)
    class Decision:
        allowed: bool
        reason: str | None = None

    async def check(self, user_id: int, requires: dict[str, object]) -> "AclCheckerProtocol.Decision": ...
