import asyncio
import signal

import grpclib.server
import structlog
from aiohttp import web

from gateway import infra
from gateway.app.consumers import NotificationsConsumer
from gateway.app.server import di
from gateway.app.server.grpc_handler import GatewayServiceHandler
from gateway.app.server.grpc_inbound_proxies import (
    MatchGrpcInboundProxy,
    ProfileGrpcInboundProxy,
    RankingGrpcInboundProxy,
)
from gateway.app.server.health import create_health_service
from gateway.app.server.http.webhook_app import create_webhook_app
from gateway.app.server.utils import configure_logger
from gateway.app.telegram.setup import configure_bot_menu, create_bot, create_dispatcher, create_fsm_storage
from gateway.infra.tracing import setup_tracing
from gateway.protocols.acl import AclCheckerProtocol
from gateway.protocols.coordination import CoordinationProtocol
from gateway.protocols.profile import ProfileServiceProtocol
from gateway.usecases.callback_routing.resolve import ResolveCallbackRoute

log = structlog.stdlib.get_logger("gateway.server")


async def run_grpc_server(service_handlers: list[object], config: infra.GrpcServerConfig) -> None:
    server = grpclib.server.Server(service_handlers)
    await server.start(config.host, config.port)
    log.info("gRPC server started", host=config.host, port=config.port)
    try:
        await server.wait_closed()
    except asyncio.CancelledError:
        log.info("gRPC server cancelled, shutting down")
        server.close()
        await server.wait_closed()


async def main() -> None:
    config = await di.container.get(infra.GlobalConfig)

    configure_logger(
        json_mode=not config.debug,
        log_level="DEBUG" if config.debug else "INFO",
    )
    setup_tracing(service_name="gateway")
    log.info("Starting gateway server")

    # gRPC: Gateway Ping + pass-through to profile, ranking, match (same service paths as backend)
    grpc_config = await di.container.get(infra.GrpcServerConfig)
    grpc_services = [
        await di.container.get(GatewayServiceHandler),
        await di.container.get(ProfileGrpcInboundProxy),
        await di.container.get(RankingGrpcInboundProxy),
        await di.container.get(MatchGrpcInboundProxy),
        create_health_service(),
    ]
    grpc_task = asyncio.create_task(run_grpc_server(grpc_services, grpc_config))

    # aiogram Bot + Dispatcher
    telegram_config: infra.TelegramConfig = await di.container.get(infra.TelegramConfig)
    valkey_config: infra.ValkeyConfig = await di.container.get(infra.ValkeyConfig)
    coordination: CoordinationProtocol = await di.container.get(CoordinationProtocol)
    resolve_usecase: ResolveCallbackRoute = await di.container.get(ResolveCallbackRoute)
    acl: AclCheckerProtocol = await di.container.get(AclCheckerProtocol)

    bot = create_bot(telegram_config.token)
    await configure_bot_menu(bot)
    log.info("Telegram bot menu configured")
    storage = create_fsm_storage(valkey_config)
    dispatcher = create_dispatcher(
        storage=storage,
        coordination=coordination,
        resolve_usecase=resolve_usecase,
        acl=acl,
        config=valkey_config,
        container=di.container,
    )

    # Установить webhook (опционально)
    if telegram_config.webhook_host:
        webhook_url = f"{telegram_config.webhook_host}{telegram_config.webhook_path}"
        _ = await bot.set_webhook(url=webhook_url, secret_token=telegram_config.webhook_secret)
        log.info("Telegram webhook set", url=webhook_url)
    else:
        log.info("webhook_host not configured, skipping set_webhook")

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

    # Notifications consumer (like.received, match.created)
    rabbitmq_config: infra.RabbitMQConfig = await di.container.get(infra.RabbitMQConfig)
    profile_service: ProfileServiceProtocol = await di.container.get(ProfileServiceProtocol)

    rabbitmq_connection_gen = infra.provide_rabbitmq_connection(rabbitmq_config)
    rabbitmq_connection = await anext(rabbitmq_connection_gen)
    notifications_consumer = NotificationsConsumer(
        connection=rabbitmq_connection,
        bot=bot,
        profile_service=profile_service,
    )
    consumer_task = asyncio.create_task(notifications_consumer.run())
    log.info("Notifications consumer started")

    log.info("Gateway started successfully")

    try:
        _ = await shutdown_event.wait()
    except KeyboardInterrupt:
        log.info("Keyboard interrupt received")
    finally:
        log.info("Stopping server")
        _ = consumer_task.cancel()
        _ = grpc_task.cancel()
        _ = await asyncio.gather(consumer_task, grpc_task, return_exceptions=True)
        await rabbitmq_connection_gen.aclose()
        await runner.cleanup()
        await bot.session.close()
        await di.container.close()
        log.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
