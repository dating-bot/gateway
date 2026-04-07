import asyncio
import signal

import grpclib.server
import structlog
from aiohttp import web

from gateway.app.server import di
from gateway.app.server.grpc_handler import GatewayServiceHandler
from gateway.app.server.health import create_health_service
from gateway.app.server.http.webhook_app import create_webhook_app
from gateway.app.server.utils import configure_logger
from gateway.app.telegram.setup import create_bot, create_dispatcher, create_fsm_storage
from gateway.infra import GlobalConfig, GrpcServerConfig
from gateway.infra.telegram import TelegramConfig
from gateway.infra.valkey import ValkeyConfig
from gateway.protocols.acl import AclCheckerProtocol
from gateway.protocols.coordination import CoordinationProtocol
from gateway.usecases.callback_routing.resolve import ResolveCallbackRoute

log = structlog.stdlib.get_logger("gateway.server")


async def run_grpc_server(handler: GatewayServiceHandler, config: GrpcServerConfig) -> None:
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
        json_mode=not config.debug,
        log_level="DEBUG" if config.debug else "INFO",
    )
    log.info("Starting gateway server")

    # gRPC task
    grpc_handler = await di.container.get(GatewayServiceHandler)
    grpc_config = await di.container.get(GrpcServerConfig)
    grpc_task = asyncio.create_task(run_grpc_server(grpc_handler, grpc_config))

    # aiogram Bot + Dispatcher
    telegram_config: TelegramConfig = await di.container.get(TelegramConfig)
    valkey_config: ValkeyConfig = await di.container.get(ValkeyConfig)
    coordination: CoordinationProtocol = await di.container.get(CoordinationProtocol)
    resolve_usecase: ResolveCallbackRoute = await di.container.get(ResolveCallbackRoute)
    acl: AclCheckerProtocol = await di.container.get(AclCheckerProtocol)

    bot = create_bot(telegram_config.token)
    storage = create_fsm_storage(valkey_config)
    dispatcher = create_dispatcher(
        storage=storage,
        coordination=coordination,
        resolve_usecase=resolve_usecase,
        acl=acl,
        config=valkey_config,
        container=di.container,
    )

    # Установить webhook
    webhook_url = f"{telegram_config.webhook_host}{telegram_config.webhook_path}"
    await bot.set_webhook(url=webhook_url, secret_token=telegram_config.webhook_secret)
    log.info("Telegram webhook set", url=webhook_url)

    # aiohttp app
    app = create_webhook_app(
        bot=bot,
        dispatcher=dispatcher,
        config=telegram_config,
        coordination=coordination,
    )

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.http_server.host, config.http_server.port)
    await site.start()
    log.info("HTTP server started", host=config.http_server.host, port=config.http_server.port)

    # Graceful shutdown
    shutdown_event = asyncio.Event()

    def _signal_handler() -> None:
        log.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    log.info("Gateway started successfully")

    try:
        await shutdown_event.wait()
    except KeyboardInterrupt:
        log.info("Keyboard interrupt received")
    finally:
        log.info("Stopping server")
        grpc_task.cancel()
        await asyncio.gather(grpc_task, return_exceptions=True)
        await runner.cleanup()
        await bot.session.close()
        await di.container.close()
        log.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
