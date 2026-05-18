"""aiohttp-приложение: webhook Telegram + health/ready/metrics эндпоинты."""

from collections.abc import Awaitable, Callable

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from gateway.infra.telegram import TelegramConfig
from gateway.infra.tracing import attach_context_from_headers
from gateway.protocols.coordination import CoordinationProtocol

type RequestHandler = Callable[[web.Request], Awaitable[web.StreamResponse]]
tracer = trace.get_tracer("gateway.http.server")


async def _health_handler(_: web.Request) -> web.Response:
    return web.Response(text="ok")


async def _ready_handler(request: web.Request) -> web.Response:
    coordination: CoordinationProtocol = request.app["coordination"]
    ok = await coordination.ping()
    if ok:
        return web.Response(text="ready")
    return web.Response(text="not ready", status=503)


async def _metrics_handler(_: web.Request) -> web.Response:
    data = generate_latest()
    return web.Response(body=data, headers={"Content-Type": CONTENT_TYPE_LATEST})


@web.middleware
async def _otel_middleware(request: web.Request, handler: RequestHandler) -> web.StreamResponse:
    route = request.match_info.route
    path_template = request.path
    if route is not None and getattr(route, "resource", None) is not None:
        canonical = getattr(route.resource, "canonical", None)
        if canonical:
            path_template = str(canonical)

    with attach_context_from_headers(request.headers):
        with tracer.start_as_current_span(f"HTTP {request.method} {path_template}", kind=SpanKind.SERVER) as span:
            span.set_attribute("http.request.method", request.method)
            span.set_attribute("url.path", request.path)
            span.set_attribute("http.route", path_template)
            response = await handler(request)
            span.set_attribute("http.response.status_code", response.status)
            return response


def create_webhook_app(
    *,
    bot: Bot,
    dispatcher: Dispatcher,
    config: TelegramConfig,
    coordination: CoordinationProtocol,
) -> web.Application:
    """Создать aiohttp Application с webhook + служебными роутами."""
    app = web.Application(middlewares=[_otel_middleware])

    app["coordination"] = coordination

    _ = app.router.add_get("/health", _health_handler)
    _ = app.router.add_get("/ready", _ready_handler)
    _ = app.router.add_get("/metrics", _metrics_handler)

    # Регистрируем aiogram webhook handler на /webhook
    SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=config.webhook_secret,
    ).register(app, path=config.webhook_path)

    setup_application(app, dispatcher, bot=bot)

    return app
