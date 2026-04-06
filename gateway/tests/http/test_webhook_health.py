from http import HTTPStatus

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.app.http.webhook_app import health_handler, ready_handler


@pytest.mark.asyncio
async def test_health_returns_ok() -> None:
    app = web.Application()
    app.router.add_get("/health", health_handler)
    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/health")
        assert resp.status == HTTPStatus.OK
        assert await resp.text() == "ok"


@pytest.mark.asyncio
async def test_ready_returns_ok() -> None:
    app = web.Application()
    app.router.add_get("/ready", ready_handler)
    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/ready")
        assert resp.status == HTTPStatus.OK
        assert await resp.text() == "ok"
