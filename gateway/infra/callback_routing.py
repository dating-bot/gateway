from pathlib import Path

from pydantic import BaseModel, Field


class CallbackRoutingConfig(BaseModel):
    routes_file: Path | None = Field(
        default=None,
        description="Path to routes.yaml (relative to cwd or absolute). If set, file must exist.",
    )
