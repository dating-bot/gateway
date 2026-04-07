import pathlib
from typing import final

import aiogram
import dishka
import glide
from dishka.integrations.aiogram import AiogramProvider
from profile_api.v1.profile_grpc import ProfileServiceStub

from gateway import adapters, infra, protocols, usecases
from gateway.app.server import grpc_handler
from gateway.app.server.telegram.handlers import register_handlers
from gateway.app.server.telegram.middlewares.callback_dispatch import CallbackRadixAclMiddleware
from gateway.app.server.telegram.middlewares.lock_user import LockUserMiddleware
from gateway.app.server.telegram.middlewares.rate_limit import RateLimitMiddleware


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

    profile_stub = dishka.provide(staticmethod(infra.provide_profile_stub))
    """gRPC-стаб для profile_service"""

    @dishka.provide
    def profile_service_adapter(self, stub: ProfileServiceStub) -> protocols.ProfileServiceProtocol:
        """адаптер profile_service (gRPC-клиент)"""
        return adapters.ProfileServiceClientAdapter(_stub=stub)

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
    def acl_adapter(
        self,
        profile_service: protocols.ProfileServiceProtocol,
        cache: protocols.CacheProtocol,
    ) -> protocols.AclChecker:
        """ACL на основе profile_service: active = профиль существует"""
        return adapters.ProfileAclAdapter(profile_service=profile_service, cache=cache)


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

    @dishka.provide
    def get_profile(
        self,
        profile_service: protocols.ProfileServiceProtocol,
        cache: protocols.CacheProtocol,
    ) -> usecases.GetProfile:
        """юзкейс получения профиля с cache-aside"""
        return usecases.GetProfile(profile_service=profile_service, cache=cache)

    @dishka.provide
    def invalidate_profile(self, cache: protocols.CacheProtocol) -> usecases.InvalidateProfile:
        """юзкейс инвалидации профиля из кэша"""
        return usecases.InvalidateProfile(cache=cache)

    @dishka.provide
    def create_profile(
        self,
        profile_service: protocols.ProfileServiceProtocol,
        get_profile: usecases.GetProfile,
    ) -> usecases.CreateProfile:
        """создание профиля в profile_service + обновление кэша через GetProfile"""
        return usecases.CreateProfile(profile_service=profile_service, get_profile=get_profile)

    @dishka.provide
    def update_profile(
        self,
        profile_service: protocols.ProfileServiceProtocol,
        invalidate_profile: usecases.InvalidateProfile,
        get_profile: usecases.GetProfile,
    ) -> usecases.UpdateProfile:
        """обновление профиля + инвалидация кэша и перезагрузка через GetProfile"""
        return usecases.UpdateProfile(
            profile_service=profile_service,
            invalidate_profile=invalidate_profile,
            get_profile=get_profile,
        )

    @dishka.provide
    def set_geo(
        self,
        profile_service: protocols.ProfileServiceProtocol,
        invalidate_profile: usecases.InvalidateProfile,
    ) -> usecases.SetGeo:
        """сохранение координат в profile_service + сброс кэша"""
        return usecases.SetGeo(profile_service=profile_service, invalidate_profile=invalidate_profile)

    @dishka.provide
    def upload_profile_photo(
        self,
        profile_service: protocols.ProfileServiceProtocol,
        invalidate_profile: usecases.InvalidateProfile,
    ) -> usecases.UploadProfilePhoto:
        return usecases.UploadProfilePhoto(
            profile_service=profile_service,
            invalidate_profile=invalidate_profile,
        )


def build_container() -> dishka.AsyncContainer:
    return dishka.make_async_container(
        InfraProvider(),
        AdapterProvider(),
        TelegramProvider(),
        AiogramProvider(),
        AppProvider(),
    )


container = build_container()
