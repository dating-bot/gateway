from typing import Protocol

from gateway.domain.resolved_callback import ResolvedCallback


class CallbackRouterProtocol(Protocol):
    def match(
        self,
        callback_data: str,
    ) -> ResolvedCallback | None: ...

    def register(
        self,
        handler_id: str,
        path_params: dict[str, str],
        requires: dict[str, object] | None = None,
    ) -> None: ...
