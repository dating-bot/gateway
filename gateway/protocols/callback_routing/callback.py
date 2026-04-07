from typing import Protocol

from gateway.domain.resolved_callback import ResolvedCallback


class CallbackRouterProtocol(Protocol):
    def match(
        self,
        callback_data: str,
    ) -> ResolvedCallback | None: ...

    def register(
        self,
        path_params: str,
        handler_id: str,
        requires: dict[str, object] | None = None,
    ) -> None: ...
