"""Сборка aiogram Dispatcher: middleware + роутеры."""

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from dishka import AsyncContainer
from dishka.integrations.aiogram import setup_dishka
from redis.asyncio import Redis

from gateway.app.telegram.fsm.registration import registration_router
from gateway.app.telegram.handlers.callback_reply import callback_router
from gateway.app.telegram.handlers.commands import commands_router
from gateway.app.telegram.middleware import (
    CallbackRadixAclMiddleware,
    LockUserMiddleware,
    RateLimitMiddleware,
)
from gateway.infra.valkey import ValkeyConfig
from gateway.protocols.acl import AclCheckerProtocol
from gateway.protocols.coordination import CoordinationProtocol
from gateway.usecases.callback_routing.resolve import ResolveCallbackRoute


def create_bot(token: str) -> Bot:
    """Создать aiogram Bot."""
    return Bot(token=token)


def create_fsm_storage(config: ValkeyConfig) -> RedisStorage:
    """Redis-based FSM хранилище на Valkey DB 0."""
    redis = Redis(host=config.host, port=config.port, db=config.fsm_db)
    return RedisStorage(redis=redis)


def create_dispatcher(
    *,
    storage: RedisStorage,
    coordination: CoordinationProtocol,
    resolve_usecase: ResolveCallbackRoute,
    acl: AclCheckerProtocol,
    config: ValkeyConfig,
    container: AsyncContainer,
) -> Dispatcher:
    """Собрать Dispatcher с middleware-цепочкой и роутерами."""
    dp = Dispatcher(storage=storage)

    # Подключить dishka для инъекции usecase'ов в хендлеры
    setup_dishka(container=container, router=dp)

    # Порядок middleware важен: RateLimit → Lock → AclRadix
    dp.update.outer_middleware(RateLimitMiddleware(coordination=coordination, limit=config.rate_limit_per_minute))
    dp.update.outer_middleware(LockUserMiddleware(coordination=coordination, lock_ttl_sec=config.user_lock_ttl_sec))
    dp.update.outer_middleware(CallbackRadixAclMiddleware(resolve_usecase=resolve_usecase, acl=acl))

    # Роутеры
    dp.include_router(commands_router)
    dp.include_router(registration_router)
    dp.include_router(callback_router)

    return dp
