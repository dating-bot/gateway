from dataclasses import dataclass
from typing import final, override

import structlog

from gateway.app.server.utils import unary
from gateway_api.v1 import gateway_pb2
from gateway_api.v1.gateway_grpc import GatewayServiceBase

log = structlog.stdlib.get_logger("gateway.grpc")


@final
@dataclass(slots=True)
class GatewayServiceHandler(GatewayServiceBase):
    @override
    @unary
    async def Ping(self, request: gateway_pb2.PingRequest) -> gateway_pb2.PingResponse:
        del request
        log.info("ping")
        return gateway_pb2.PingResponse(message="pong")
