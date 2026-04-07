from typing import final, override

from gateway.pkg.routing.radix_tree import MatchResult, RadixTree
from gateway.protocols.callback_router import CallbackRouterProtocol


@final
class RadixCallbackRouterAdapter(CallbackRouterProtocol):
    """Адаптер CallbackRouterProtocol на основе RadixTree."""

    def __init__(self) -> None:
        self._tree = RadixTree()

    @override
    def match(self, path: str) -> MatchResult | None:
        return self._tree.match(path)

    @override
    def insert(self, path: str, handler_id: str, requires: dict[str, object]) -> None:
        self._tree.insert(path, handler_id, requires)
