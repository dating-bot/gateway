import asyncio
import signal

import grpclib.server
import structlog
from aiogram import Dispatcher, Router
from dishka.integrations.aiogram import setup_dishka

from gateway.app.http.webhook_app import create_aiohttp_app, start_http_runner
from gateway.app.server import di
from gateway.app.server.grpc_handler import GatewayServiceHandler
from gateway.app.server.health import create_health_service
from gateway.app.server.utils import configure_logger
from gateway.app.telegram.handlers import register_handlers
from gateway.infra import GlobalConfig, GrpcServerConfig, HttpServerConfig, TelegramBotConfig

log = structlog.stdlib.get_logger("gateway.server")


async def run_grpc_server(
    handler: GatewayServiceHandler,
    config: GrpcServerConfig,
) -> None:
    server = grpclib.server.Server([handler, create_health_service()])
    await server.start(config.host, config.port)
    log.info("gRPC server started", host=config.host, port=config.port)

    try:
        await server.wait_closed()
    except asyncio.CancelledError:
        log.info("gRPC server cancelled, shutting down")
        server.close()
        await server.wait_closed()


async def main() -> None:
    config = await di.container.get(GlobalConfig)

    configure_logger(
        json_mode=False,
        log_level="DEBUG" if config.debug else "INFO",
    )
    log.info("Starting gateway server")

    telegram_cfg = await di.container.get(TelegramBotConfig)
    if telegram_cfg.is_using_placeholder_token():
        log.warning(
            "telegram.bot_token is empty; using dev placeholder (set GATEWAY_TELEGRAM__BOT_TOKEN for production)",
        )

    router = await di.container.get(Router)
    register_handlers(router)
    dispatcher = await di.container.get(Dispatcher)
    setup_dishka(di.container, dispatcher, auto_inject=True)

    http_app = await create_aiohttp_app(di.container)
    http_cfg = await di.container.get(HttpServerConfig)
    http_runner = await start_http_runner(http_app, http_cfg.host, http_cfg.port)
    log.info("HTTP webhook server listening", host=http_cfg.host, port=http_cfg.port)

    grpc_handler_instance = await di.container.get(GatewayServiceHandler)
    grpc_config = await di.container.get(GrpcServerConfig)

    shutdown_event = asyncio.Event()

    def signal_handler() -> None:
        log.info("Shutdown signal received, stopping server")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    grpc_task = asyncio.create_task(run_grpc_server(grpc_handler_instance, grpc_config))

    log.info("Server started successfully")

    try:
        _ = await shutdown_event.wait()
    except KeyboardInterrupt:
        log.info("Keyboard interrupt received")
    finally:
        log.info("Stopping server")
        _ = grpc_task.cancel()
        _ = await asyncio.gather(grpc_task, return_exceptions=True)
        await http_runner.cleanup()
        await di.container.close()
        log.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
