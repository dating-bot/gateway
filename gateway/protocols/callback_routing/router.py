from typing import Protocol

from gateway.domain.resolved_callback import ResolvedCallback


class CallbackRouterProtocol(Protocol):
    def match(self, callback_data: str) -> ResolvedCallback | None: ...
