from typing import ClassVar, final

import pydantic
import structlog

from gateway.domain.resolved_callback import ResolvedCallback
from gateway.protocols.callback_routing.callback import CallbackRouterProtocol

log = structlog.stdlib.get_logger("gateway.usecases.callback_routing.ResolveCallbackRoute")


class ResolveCallbackRouteError(Exception): ...


class ResolveCallbackRouteInvalidDataError(ResolveCallbackRouteError):
    """Invalid input data (empty callback_data)."""


@final
class ResolveCallbackRoute:
    def __init__(self, *, router: CallbackRouterProtocol) -> None:
        self._router = router

    class Request(pydantic.BaseModel):
        callback_data: str

    class Response(pydantic.BaseModel):
        resolved: ResolvedCallback | None

        model_config: ClassVar[pydantic.ConfigDict] = pydantic.ConfigDict(arbitrary_types_allowed=True)

    def execute(self, request: Request) -> Response:
        if not request.callback_data:
            raise ResolveCallbackRouteInvalidDataError("callback_data cannot be empty")
        log.debug("resolving callback route", callback_data=request.callback_data)
        resolved = self._router.match(request.callback_data)
        if resolved is None:
            log.debug("route not found", callback_data=request.callback_data)
        else:
            log.debug("route resolved", handler_id=resolved.handler_id, callback_data=request.callback_data)
        return self.Response(resolved=resolved)
