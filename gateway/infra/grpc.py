from pydantic import BaseModel, Field


class GrpcServerConfig(BaseModel):
    host: str = Field(default="0.0.0.0", description="gRPC server host")  # noqa: S104
    port: int = Field(default=50051, description="gRPC server port")
