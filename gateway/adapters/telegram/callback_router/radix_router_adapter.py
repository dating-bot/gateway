from dataclasses import dataclass, field
from typing import final, override

from gateway.domain.resolved_callback import ResolvedCallback
from gateway.pkg.routing.radix_tree import RadixTree
from gateway.protocols.callback_routing.router import CallbackRouterProtocol


@final
@dataclass(slots=True)
class RadixCallbackRouterAdapter(CallbackRouterProtocol):
    _tree: RadixTree = field(default_factory=RadixTree)

    @override
    def match(self, callback_data: str) -> ResolvedCallback | None:
        raw = self._tree.match(callback_data)
        if raw is None:
            return None
        return ResolvedCallback(
            handler_id=raw.handler,
            path_params=raw.params,
            requires=raw.requires,
        )

    def register_route(
        self,
        path: str,
        handler_id: str,
        requires: dict[str, object] | None = None,
    ) -> None:
        self._tree.insert(path, handler_id, requires)
