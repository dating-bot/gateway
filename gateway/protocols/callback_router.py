from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class MatchResult:
    """Результат поиска маршрута в radix tree."""

    handler_id: str
    path_params: dict[str, str] = field(default_factory=dict)
    requires: dict[str, object] = field(default_factory=dict)


class CallbackRouterProtocol(Protocol):
    """Маршрутизатор callback_data через radix tree."""

    def match(self, path: str) -> MatchResult | None:
        """Найти маршрут по callback_data. O(k), k — число сегментов."""
        ...

    def insert(self, path: str, handler_id: str, requires: dict[str, object]) -> None:
        """Зарегистрировать маршрут в дереве."""
        ...
