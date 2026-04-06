from typing import final

import dishka
from aiogram import Bot, Dispatcher, Router
from dishka.integrations.aiogram import AiogramProvider

from gateway import adapters, infra, protocols, usecases
from gateway.app.server import grpc_handler


@final
class InfraProvider(dishka.Provider):
    scope = dishka.Scope.APP

    global_config = dishka.provide(staticmethod(infra.GlobalConfig.load))
    subconfigs = dishka.provide_all(*infra.GlobalConfig.subconfigs())


@final
class TelegramProvider(dishka.Provider):
    scope = dishka.Scope.APP

    @dishka.provide
    def provide_bot(self, cfg: infra.TelegramBotConfig) -> Bot:
        return Bot(token=cfg.effective_bot_token())

    @dishka.provide
    def provide_router(self) -> Router:
        return Router()

    @dishka.provide
    def provide_dispatcher(self, router: Router) -> Dispatcher:
        dp = Dispatcher()
        _ = dp.include_router(router)
        return dp


@final
class AppProvider(dishka.Provider):
    scope = dishka.Scope.APP

    grpc_service_handler = dishka.provide(grpc_handler.GatewayServiceHandler)

    @dishka.provide
    def radix_callback_router(self) -> protocols.CallbackRouterProtocol:
        return adapters.RadixCallbackRouterAdapter()

    resolve_callback_route = dishka.provide(usecases.ResolveCallbackRouteUsecase)


container = dishka.make_async_container(
    InfraProvider(),
    TelegramProvider(),
    AiogramProvider(),
    AppProvider(),
)
