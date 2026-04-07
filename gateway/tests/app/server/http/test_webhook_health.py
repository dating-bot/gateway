from http import HTTPStatus
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

if TYPE_CHECKING:
    from dishka import AsyncContainer

from gateway.app.server.http.webhook_app import CONTAINER_KEY, health_handler, ready_handler
from gateway.protocols.coordination import CoordinationProtocol


@pytest.mark.asyncio
async def test_health_returns_ok() -> None:
    app = web.Application()
    app.router.add_get("/health", health_handler)
    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/health")
        assert resp.status == HTTPStatus.OK
        assert await resp.text() == "ok"


@pytest.mark.asyncio
async def test_ready_returns_ok_when_valkey_up() -> None:
    valkey = MagicMock(spec=CoordinationProtocol)
    valkey.ping = AsyncMock(return_value=True)
    container = MagicMock()
    container.get = AsyncMock(return_value=valkey)

    app = web.Application()
    app[CONTAINER_KEY] = cast("AsyncContainer", container)
    app.router.add_get("/ready", ready_handler)
    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/ready")
        assert resp.status == HTTPStatus.OK
        assert await resp.text() == "ok"


@pytest.mark.asyncio
async def test_ready_returns_503_when_valkey_down() -> None:
    valkey = MagicMock(spec=CoordinationProtocol)
    valkey.ping = AsyncMock(return_value=False)
    container = MagicMock()
    container.get = AsyncMock(return_value=valkey)

    app = web.Application()
    app[CONTAINER_KEY] = cast("AsyncContainer", container)
    app.router.add_get("/ready", ready_handler)
    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/ready")
        assert resp.status == HTTPStatus.SERVICE_UNAVAILABLE
