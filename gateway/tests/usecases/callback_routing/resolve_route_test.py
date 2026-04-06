from gateway.domain.resolved_callback import ResolvedCallback
from gateway.protocols.callback_routing.router import CallbackRouterProtocol
from gateway.usecases.callback_routing.resolve_route import ResolveCallbackRouteUsecase


class FakeRouter:
    def match(self, callback_data: str) -> ResolvedCallback | None:
        if callback_data == "like":
            return ResolvedCallback(
                handler_id="handle_like",
                path_params={},
                requires={"active": True},
            )
        return None


def test_resolve_callback_route_delegates_to_port():
    router: CallbackRouterProtocol = FakeRouter()
    usecase = ResolveCallbackRouteUsecase(router)

    r = usecase.execute("like")
    assert r is not None
    assert r.handler_id == "handle_like"

    assert usecase.execute("nope") is None
