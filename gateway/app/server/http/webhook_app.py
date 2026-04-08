"""aiohttp-приложение: webhook Telegram + health/ready/metrics эндпоинты."""

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from gateway.infra.telegram import TelegramConfig
from gateway.protocols.coordination import CoordinationProtocol


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
    return web.Response(body=data, content_type=CONTENT_TYPE_LATEST)


def create_webhook_app(
    *,
    bot: Bot,
    dispatcher: Dispatcher,
    config: TelegramConfig,
    coordination: CoordinationProtocol,
) -> web.Application:
    """Создать aiohttp Application с webhook + служебными роутами."""
    app = web.Application()

    app["coordination"] = coordination

    app.router.add_get("/health", _health_handler)
    app.router.add_get("/ready", _ready_handler)
    app.router.add_get("/metrics", _metrics_handler)

    # Регистрируем aiogram webhook handler на /webhook
    SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=config.webhook_secret,
    ).register(app, path=config.webhook_path)

    setup_application(app, dispatcher, bot=bot)

    return app
