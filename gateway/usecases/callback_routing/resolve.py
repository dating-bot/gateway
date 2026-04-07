from typing import final

import structlog

from gateway.domain.resolved_callback import ResolvedCallback
from gateway.infra.metrics import radix_tree_unmatched_total
from gateway.protocols.callback_router import CallbackRouterProtocol

log = structlog.stdlib.get_logger("gateway.usecases.ResolveCallbackRoute")


@final
class ResolveCallbackRoute:
    def __init__(self, *, router: CallbackRouterProtocol) -> None:
        self._router = router

    def execute(self, callback_data: str) -> ResolvedCallback | None:
        result = self._router.match(callback_data)
        if result is None:
            radix_tree_unmatched_total.inc()
            log.debug("callback route not found", callback_data=callback_data)
            return None
        log.debug(
            "callback route resolved",
            callback_data=callback_data,
            handler_id=result.handler_id,
            path_params=result.path_params,
        )
        return ResolvedCallback(
            handler_id=result.handler_id,
            path_params=result.path_params,
            requires=result.requires,
        )
