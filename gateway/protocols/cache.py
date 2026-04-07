from collections.abc import Callable
from datetime import timedelta
from typing import Protocol, overload


class CacheProtocol(Protocol):
    """Кэш произвольных значений через сериализацию в bytes."""

    @overload
    async def get(self, key: str) -> bytes | None: ...

    @overload
    async def get[T](self, key: str, *, unmarshal_as: type[T]) -> T | None: ...

    @overload
    async def get[T](self, key: str, *, unmarshal_using: Callable[[bytes], T]) -> T | None: ...

    async def get[T](  # type: ignore[misc]
        self,
        key: str,
        *,
        unmarshal_as: type[T] | None = None,
        unmarshal_using: Callable[[bytes], T] | None = None,
    ) -> T | None: ...

    async def set[T](
        self,
        key: str,
        value: T,
        *,
        ttl: timedelta | None = None,
        marshal_using: Callable[[T], bytes] | None = None,
    ) -> None: ...

    async def delete(self, key: str) -> None: ...
