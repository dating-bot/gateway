from pydantic import BaseModel, Field


class CallbackRoutingConfig(BaseModel):
    routes_file: str = Field(description="Путь к YAML-файлу маршрутов callback_data")
