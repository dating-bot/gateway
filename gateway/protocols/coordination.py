from typing import Protocol


class CoordinationProtocol(Protocol):
    """Атомарные операции в Valkey для rate limiting и distributed locking."""

    async def ping(self) -> bool: ...

    async def incr_with_expire(self, key: str, expire_sec: int) -> int:
        """INCR + EXPIRE (если count == 1). Возвращает новое значение счётчика."""
        ...

    async def set_nx(self, key: str, value: str, ttl_sec: int) -> bool:
        """SET key value NX EX ttl. Возвращает True если lock получен."""
        ...

    async def delete(self, key: str) -> None: ...
