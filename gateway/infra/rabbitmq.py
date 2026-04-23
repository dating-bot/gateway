from pydantic import BaseModel


class RabbitMQConfig(BaseModel):
    host: str
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtualhost: str = "/"

    @property
    def url(self) -> str:
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}{self.virtualhost}"