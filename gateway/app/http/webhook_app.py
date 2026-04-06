from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dishka import AsyncContainer

from gateway.infra.telegram import TelegramBotConfig


async def health_handler(_: web.Request) -> web.Response:
    return web.Response(text="ok")


async def ready_handler(_: web.Request) -> web.Response:
    return web.Response(text="ok")


async def create_aiohttp_app(container: AsyncContainer) -> web.Application:
    app = web.Application()
    _ = app.router.add_get("/health", health_handler)
    _ = app.router.add_get("/ready", ready_handler)

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

    return app


async def start_http_runner(app: web.Application, host: str, port: int) -> web.AppRunner:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    return runner
