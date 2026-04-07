from typing import Protocol


class AclCheckerProtocol(Protocol):
    """Проверка прав доступа по требованиям маршрута."""

    async def check(self, user_id: int, requires: dict[str, object]) -> bool:
        """Вернуть True если пользователь удовлетворяет всем requires."""
        ...
