import pytest

from gateway.domain.resolved_callback import ResolvedCallback
from gateway.protocols.callback_routing.callback import CallbackRouterProtocol
from gateway.usecases.callback_routing.resolve_route import (
    ResolveCallbackRoute,
    ResolveCallbackRouteInvalidDataError,
)


class FakeRouter:
    def match(self, callback_data: str) -> ResolvedCallback | None:
        if callback_data == "like":
            return ResolvedCallback(
                handler_id="handle_like",
                path_params={},
                requires={"active": True},
            )
        return None

    def register(self, path_params: str, handler_id: str, requires: dict[str, object] | None = None) -> None:
        pass


def test_resolve_callback_route_found() -> None:
    router: CallbackRouterProtocol = FakeRouter()
    usecase = ResolveCallbackRoute(router=router)

    response = usecase.execute(ResolveCallbackRoute.Request(callback_data="like"))
    assert response.resolved is not None
    assert response.resolved.handler_id == "handle_like"


def test_resolve_callback_route_not_found() -> None:
    router: CallbackRouterProtocol = FakeRouter()
    usecase = ResolveCallbackRoute(router=router)

    response = usecase.execute(ResolveCallbackRoute.Request(callback_data="nope"))
    assert response.resolved is None


def test_resolve_callback_route_empty_data_raises() -> None:
    router: CallbackRouterProtocol = FakeRouter()
    usecase = ResolveCallbackRoute(router=router)

    with pytest.raises(ResolveCallbackRouteInvalidDataError):
        usecase.execute(ResolveCallbackRoute.Request(callback_data=""))
