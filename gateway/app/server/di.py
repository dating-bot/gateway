from typing import final

import dishka

from external_clients.match_api.v1.match_grpc import MatchServiceStub
from external_clients.profile_api.v1.profile_grpc import ProfileServiceStub
from external_clients.ranking_api.v1.ranking_grpc import RankingServiceStub
from gateway.adapters import (
    GrpcProfileServiceAdapter,
    MatchServiceAdapter,
    ProfileAclAdapter,
    RadixCallbackRouterAdapter,
    ValkeyCacheAdapter,
    ValkeyCoordinationAdapter,
)
from gateway.app.server import grpc_handler
from gateway.infra import (
    CallbackRoutingConfig,
    GlobalConfig,
    provide_glide_client,
    provide_match_stub,
    provide_profile_stub,
    provide_ranking_stub,
)
from gateway.infra.callback_routes_yaml import load_routes_from_yaml_file
from gateway.protocols import (
    AclCheckerProtocol,
    CacheProtocol,
    CallbackRouterProtocol,
    CoordinationProtocol,
    MatchServiceProtocol,
    ProfileServiceProtocol,
)
from gateway.usecases import (
    CreateProfile,
    DeletePhoto,
    GetProfile,
    ResolveCallbackRoute,
    SetGeo,
    UpdateProfile,
    UploadPhoto,
)


@final
class InfraProvider(dishka.Provider):
    scope = dishka.Scope.APP

    global_config = dishka.provide(staticmethod(GlobalConfig.load))
    """глобальный конфиг"""

    subconfigs = dishka.provide_all(*GlobalConfig.subconfigs())
    """все вложенные конфиги из GlobalConfig"""

    glide_client = dishka.provide(staticmethod(provide_glide_client))
    """GlideClient (Rust) для кэша и coordination"""

    profile_stub = dishka.provide(staticmethod(provide_profile_stub), provides=ProfileServiceStub)
    """gRPC-stub к profile-service"""

    match_stub = dishka.provide(staticmethod(provide_match_stub), provides=MatchServiceStub)
    """gRPC-stub к match-service"""

    ranking_stub = dishka.provide(staticmethod(provide_ranking_stub), provides=RankingServiceStub)
    """gRPC-stub к ranking-service"""


@final
class AdapterProvider(dishka.Provider):
    scope = dishka.Scope.APP

    coordination_adapter = dishka.provide(
        source=ValkeyCoordinationAdapter,
        provides=CoordinationProtocol,
    )
    """адаптер coordination (rate limit, lock) на Valkey"""

    cache_adapter = dishka.provide(
        source=ValkeyCacheAdapter,
        provides=CacheProtocol,
    )
    """адаптер кэша на Valkey"""

    profile_service_adapter = dishka.provide(
        source=GrpcProfileServiceAdapter,
        provides=ProfileServiceProtocol,
    )
    """адаптер profile-service через gRPC"""

    match_service_adapter = dishka.provide(
        source=MatchServiceAdapter,
        provides=MatchServiceProtocol,
    )
    """адаптер match-service через gRPC"""

    ranking_service_adapter = dishka.provide(
        source=RankingServiceAdapter,
        provides=RankingServiceProtocol,
    )
    """адаптер ranking-service через gRPC"""

    acl_adapter = dishka.provide(
        source=ProfileAclAdapter,
        provides=AclCheckerProtocol,
    )
    """адаптер ACL-проверки"""

    @dishka.provide(provides=CallbackRouterProtocol)
    def provide_callback_router(self, config: CallbackRoutingConfig) -> CallbackRouterProtocol:
        """Radix tree маршрутизатор, загружается из routes.yaml при старте."""
        adapter = RadixCallbackRouterAdapter()
        load_routes_from_yaml_file(config.routes_file, adapter)
        return adapter


@final
class UsecaseProvider(dishka.Provider):
    scope = dishka.Scope.APP

    resolve_callback = dishka.provide(ResolveCallbackRoute)
    """use case разбора callback_data через radix tree"""

    get_profile = dishka.provide(GetProfile)
    """use case получения профиля (cache-aside)"""

    create_profile = dishka.provide(CreateProfile)
    """use case создания профиля"""

    update_profile = dishka.provide(UpdateProfile)
    """use case обновления профиля"""

    set_geo = dishka.provide(SetGeo)
    """use case обновления геолокации"""

    upload_photo = dishka.provide(UploadPhoto)
    """use case загрузки фото"""

    delete_photo = dishka.provide(DeletePhoto)
    """use case удаления фото"""


@final
class AppProvider(dishka.Provider):
    scope = dishka.Scope.APP

    grpc_service_handler = dishka.provide(grpc_handler.GatewayServiceHandler)
    """gRPC-обработчик GatewayService"""


container = dishka.make_async_container(
    InfraProvider(),
    AdapterProvider(),
    UsecaseProvider(),
    AppProvider(),
)
