from dataclasses import dataclass
from typing import final

from gateway.domain.resolved_callback import ResolvedCallback
from gateway.protocols.callback_routing.protocol import CallbackRouterProtocol


@final
@dataclass(slots=True)
class ResolveCallbackRouteUsecase:
    _router: CallbackRouterProtocol

    def execute(self, callback_data: str) -> ResolvedCallback | None:
        return self._router.match(callback_data)
