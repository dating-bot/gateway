from collections.abc import AsyncGenerator

import grpclib.client
from profile_api.v1.profile_grpc import ProfileServiceStub
from pydantic import BaseModel, Field


class ProfileServiceConfig(BaseModel):
    address: str = Field(default="profile_service:50052", description="Profile service gRPC address (host:port)")

    @property
    def host(self) -> str:
        return self.address.rsplit(":", 1)[0]

    @property
    def port(self) -> int:
        return int(self.address.rsplit(":", 1)[1])


async def provide_profile_stub(config: ProfileServiceConfig) -> AsyncGenerator[ProfileServiceStub]:
    """gRPC-клиент profile_service; канал открывается и закрывается вместе с приложением."""
    channel = grpclib.client.Channel(host=config.host, port=config.port)
    try:
        yield ProfileServiceStub(channel)
    finally:
        channel.close()
