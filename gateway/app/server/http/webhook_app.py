from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dishka import AsyncContainer
from prometheus_client import generate_latest

from gateway.infra.telegram import TelegramBotConfig
from gateway.protocols.coordination import CoordinationProtocol

CONTAINER_KEY: web.AppKey[AsyncContainer] = web.AppKey("dishka_container", AsyncContainer)


async def health_handler(_: web.Request) -> web.Response:
    return web.Response(text="ok")


async def ready_handler(request: web.Request) -> web.Response:
    container = request.app[CONTAINER_KEY]
    valkey = await container.get(CoordinationProtocol)
    if not await valkey.ping():
        return web.Response(text="valkey unavailable", status=503)
    return web.Response(text="ok")


async def metrics_handler(_: web.Request) -> web.Response:
    return web.Response(
        body=generate_latest(),
        content_type="text/plain; version=1.0.0",
        charset="utf-8",
    )


def _register_monitoring_routes(app: web.Application) -> None:
    _ = app.router.add_get("/health", health_handler)
    _ = app.router.add_get("/ready", ready_handler)
    _ = app.router.add_get("/metrics", metrics_handler)


async def _register_telegram_webhook(app: web.Application, container: AsyncContainer) -> None:
    bot = await container.get(Bot)
    dispatcher = await container.get(Dispatcher)
    telegram_cfg = await container.get(TelegramBotConfig)

    setup_application(app, dispatcher, bot=bot)

    secret = telegram_cfg.webhook_secret_token
    if secret is not None and secret.strip() == "":
        secret = None

    webhook_handler = SimpleRequestHandler(
        dispatcher,
        bot,
        handle_in_background=True,
        secret_token=secret,
    )
    webhook_handler.register(app, path=telegram_cfg.webhook_path)


async def create_aiohttp_app(container: AsyncContainer) -> web.Application:
    app = web.Application()
    app[CONTAINER_KEY] = container
    _register_monitoring_routes(app)
    await _register_telegram_webhook(app, container)
    return app


async def start_http_runner(app: web.Application, host: str, port: int) -> web.AppRunner:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    return runner
