from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class MatchResult:
    handler_id: str
    path_params: dict[str, str] = field(default_factory=dict)
    requires: dict[str, object] = field(default_factory=dict)


class CallbackRouterProtocol(Protocol):
    def match(self, path: str) -> MatchResult | None: ...

    def insert(self, path: str, handler_id: str, requires: dict[str, object]) -> None: ...
