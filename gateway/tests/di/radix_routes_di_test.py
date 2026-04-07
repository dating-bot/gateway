import pytest

from gateway.app.server.di import container
from gateway.usecases.callback_routing.resolve_route import ResolveCallbackRoute


@pytest.mark.asyncio
async def test_resolve_route_usecase_loads_like_from_config_toml() -> None:
    usecase = await container.get(ResolveCallbackRoute)
    response = usecase.execute(ResolveCallbackRoute.Request(callback_data="like"))
    assert response.resolved is not None
    assert response.resolved.handler_id == "handle_like"
    assert response.resolved.requires.get("active") is True
