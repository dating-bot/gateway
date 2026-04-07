import pathlib
from typing import final

import aiogram
import dishka
import glide
from dishka.integrations.aiogram import AiogramProvider

from gateway import adapters, infra, protocols, usecases
from gateway.app.server import grpc_handler
from gateway.app.server.telegram.handlers import register_handlers
from gateway.app.server.telegram.middlewares import (
    CallbackRadixAclMiddleware,
    LockUserMiddleware,
    RateLimitMiddleware,
)


@final
class InfraProvider(dishka.Provider):
    scope = dishka.Scope.APP

    global_config = dishka.provide(staticmethod(infra.GlobalConfig.load))
    """глобальный конфиг приложения, загружаемый из файла"""

    subconfigs = dishka.provide_all(*infra.GlobalConfig.subconfigs())
    """вложенные конфиги из глобального конфига"""

    valkey_runtime = dishka.provide(staticmethod(infra.provide_valkey_runtime))
    """FSM storage (Redis) для aiogram; закрытие в shutdown"""

    glide_client = dishka.provide(staticmethod(infra.provide_glide_client))
    """GlideClient для Valkey (rate limit / lock / cache)"""


@final
class AdapterProvider(dishka.Provider):
    scope = dishka.Scope.APP

    @dishka.provide
    def valkey_adapter(self, client: glide.GlideClient) -> protocols.CoordinationProtocol:
        """адаптер Valkey (rate limit / distributed lock)"""
        return adapters.CoordinationAdapter(client=client)

    @dishka.provide
    def cache_adapter(self, client: glide.GlideClient, cfg: infra.ValkeyConfig) -> protocols.CacheProtocol:
        """адаптер кэша (get/set/delete с marshal/unmarshal)"""
        return adapters.ValkeyCacheAdapter(client=client, config=cfg)

    @dishka.provide
    def radix_callback_router(self, cfg: infra.CallbackRoutingConfig) -> protocols.CallbackRouterProtocol:
        """адаптер radix-маршрутизатора callback_data"""
        router = adapters.RadixCallbackRouterAdapter()
        if cfg.routes_file is None:
            return router
        path = pathlib.Path(cfg.routes_file).expanduser()
        if not path.is_absolute():
            path = pathlib.Path.cwd() / path
        infra.load_routes_from_yaml_file(router, path.resolve())
        return router

    @dishka.provide
    def acl_adapter(self) -> protocols.AclChecker:
        """заглушка ACL (разрешает всё — заменить на реальный адаптер)"""
        return adapters.NullAclAdapter()


@final
class TelegramProvider(dishka.Provider):
    scope = dishka.Scope.APP

    @dishka.provide
    def provide_bot(self, cfg: infra.TelegramBotConfig) -> aiogram.Bot:
        return aiogram.Bot(token=cfg.bot_token)

    @dishka.provide
    def provide_router(self) -> aiogram.Router:
        router = aiogram.Router()
        register_handlers(router)
        return router

    @dishka.provide
    def provide_dispatcher(  # noqa:PLR0913
        self,
        router: aiogram.Router,
        runtime: infra.ValkeyRuntime,
        valkey_cfg: infra.ValkeyConfig,
        valkey: protocols.CoordinationProtocol,
        resolve_route: usecases.ResolveCallbackRoute,
        acl: protocols.AclChecker,
    ) -> aiogram.Dispatcher:
        dp = aiogram.Dispatcher(storage=runtime.storage)
        _ = dp.include_router(router)
        _ = dp.update.outer_middleware(RateLimitMiddleware(valkey, valkey_cfg))
        _ = dp.update.outer_middleware(LockUserMiddleware(valkey, valkey_cfg))
        _ = dp.update.outer_middleware(CallbackRadixAclMiddleware(resolve_route, acl))
        return dp


@final
class AppProvider(dishka.Provider):
    scope = dishka.Scope.APP

    grpc_service_handler = dishka.provide(grpc_handler.GatewayServiceHandler)

    @dishka.provide
    def resolve_callback_route(self, router: protocols.CallbackRouterProtocol) -> usecases.ResolveCallbackRoute:
        """юзкейс разрешения callback-маршрута через radix-дерево"""
        return usecases.ResolveCallbackRoute(router=router)


def build_container() -> dishka.AsyncContainer:
    return dishka.make_async_container(
        InfraProvider(),
        AdapterProvider(),
        TelegramProvider(),
        AiogramProvider(),
        AppProvider(),
    )


container = build_container()
