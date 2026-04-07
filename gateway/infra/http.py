from pydantic import BaseModel, Field


class HttpServerConfig(BaseModel):
    host: str = Field(default="0.0.0.0", description="HTTP server host")  # noqa: S104
    port: int = Field(default=8080, description="HTTP server port")
