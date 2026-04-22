from collections.abc import AsyncGenerator

import grpclib.client
from pydantic import BaseModel, Field

from external_clients.match_api.v1.match_grpc import MatchServiceStub


class MatchServiceConfig(BaseModel):
    host: str = Field(description="match-service gRPC host")
    port: int = Field(default=50052, description="match-service gRPC port")


async def provide_match_stub(config: MatchServiceConfig) -> AsyncGenerator[MatchServiceStub]:
    channel = grpclib.client.Channel(host=config.host, port=config.port)
    try:
        yield MatchServiceStub(channel)
    finally:
        channel.close()
