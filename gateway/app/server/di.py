from typing import final

import dishka

from gateway.app.server import grpc_handler
from gateway.infra import GlobalConfig


@final
class InfraProvider(dishka.Provider):
    scope = dishka.Scope.APP

    global_config = dishka.provide(staticmethod(GlobalConfig.load))
    subconfigs = dishka.provide_all(*GlobalConfig.subconfigs())


@final
class AppProvider(dishka.Provider):
    scope = dishka.Scope.APP

    grpc_service_handler = dishka.provide(grpc_handler.GatewayServiceHandler)


container = dishka.make_async_container(InfraProvider(), AppProvider())
