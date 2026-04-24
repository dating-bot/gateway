import asyncio
import json
from typing import final

import aio_pika
import aio_pika.abc
import structlog
from aiogram import Bot

from gateway.app.telegram.handlers.commands import _build_browse_kb, _send_candidate_profile
from gateway.app.telegram.handlers.profile_view import _profile_caption_html
from gateway.protocols.profile import ProfileServiceProtocol

log = structlog.stdlib.get_logger("gateway.consumers.NotificationsConsumer")

MATCH_EVENTS_EXCHANGE = "match.events"
LIKE_RECEIVED_QUEUE = "gateway.like.received"
LIKE_RECEIVED_ROUTING_KEY = "like.received"
MATCH_CREATED_QUEUE = "gateway.match.created"
MATCH_CREATED_ROUTING_KEY = "match.created"


@final
class NotificationsConsumer:
    def __init__(
        self,
        *,
        connection: aio_pika.abc.AbstractRobustConnection,
        bot: Bot,
        profile_service: ProfileServiceProtocol,
    ) -> None:
        self._connection = connection
        self._bot = bot
        self._profile_service = profile_service
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def run(self) -> None:
        """Запускает консьюмер для уведомлений."""
        channel = await self._connection.channel()
        self._channel = channel
        await channel.set_qos(prefetch_count=10)

        exchange = await channel.declare_exchange(
            MATCH_EVENTS_EXCHANGE,
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )

        like_queue = await channel.declare_queue(LIKE_RECEIVED_QUEUE, durable=True)
        await like_queue.bind(exchange, routing_key=LIKE_RECEIVED_ROUTING_KEY)

        match_queue = await channel.declare_queue(MATCH_CREATED_QUEUE, durable=True)
        await match_queue.bind(exchange, routing_key=MATCH_CREATED_ROUTING_KEY)

        log.info("notifications consumer started", queues=[LIKE_RECEIVED_QUEUE, MATCH_CREATED_QUEUE])

        try:
            async with asyncio.TaskGroup() as tg:
                _ = tg.create_task(self._consume_likes(like_queue))
                _ = tg.create_task(self._consume_matches(match_queue))
        except asyncio.CancelledError:
            log.info("notifications consumer cancelled")
        finally:
            self._channel = None

    async def stop(self) -> None:
        """Останавливает консьюмер."""
        if self._channel is not None and not self._channel.is_closed:
            await self._channel.close()

    async def _consume_likes(self, queue: aio_pika.abc.AbstractQueue) -> None:
        """Обрабатывает события like.received."""
        try:
            async with queue.iterator() as iterator:
                async for message in iterator:
                    async with message.process(ignore_processed=True):
                        await self._on_like_received(message)
        except (asyncio.CancelledError, aio_pika.exceptions.ChannelInvalidStateError):
            log.info("like consumer stopped")

    async def _consume_matches(self, queue: aio_pika.abc.AbstractQueue) -> None:
        """Обрабатывает события match.created."""
        try:
            async with queue.iterator() as iterator:
                async for message in iterator:
                    async with message.process(ignore_processed=True):
                        await self._on_match_created(message)
        except (asyncio.CancelledError, aio_pika.exceptions.ChannelInvalidStateError):
            log.info("match consumer stopped")

    async def _on_like_received(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        """Отправляет уведомление о полученном лайке."""
        try:
            data = json.loads(message.body)
            liker_telegram_id = int(data["liker_telegram_id"])
            liked_telegram_id = int(data["liked_telegram_id"])

            liker_profile = await self._profile_service.get_profile(liker_telegram_id)
            liker_name = liker_profile.name if liker_profile else "Кто-то"
            liker_username = await self._get_username(liker_telegram_id)
            liker_handle = f" ({liker_username})" if liker_username else ""

            text = (
                f"❤️ {liker_name}{liker_handle} поставил(а) тебе лайк!\n\n"
                "Вот его анкета — можешь ответить взаимно прямо сейчас 👇"
            )

            try:
                await self._bot.send_message(chat_id=liked_telegram_id, text=text)
            except Exception:
                log.warning(
                    "failed to send like intro notification (user may have blocked bot)",
                    liker=liker_telegram_id,
                    liked=liked_telegram_id,
                )
                return

            if liker_profile is None:
                _ = await self._bot.send_message(
                    chat_id=liked_telegram_id,
                    text=f"Анкета пользователя: {liker_name}",
                    reply_markup=_build_browse_kb(liker_telegram_id),
                )
                log.info(
                    "like notification sent without profile data",
                    liker=liker_telegram_id,
                    liked=liked_telegram_id,
                )
                return

            try:
                await _send_candidate_profile(
                    bot=self._bot,
                    chat_id=liked_telegram_id,
                    candidate=liker_profile,
                    profile_service=self._profile_service,
                )
            except Exception:
                log.exception(
                    "failed to send liker card, sending text fallback",
                    liker=liker_telegram_id,
                    liked=liked_telegram_id,
                )
                gender_label = {"male": "Мужчина", "female": "Женщина"}.get(liker_profile.gender.value, "—")
                fallback_text = _profile_caption_html(
                    liker_profile.name,
                    liker_profile.age,
                    liker_profile.city,
                    gender_label,
                    liker_profile.bio,
                )
                _ = await self._bot.send_message(
                    chat_id=liked_telegram_id,
                    text=fallback_text,
                    parse_mode="HTML",
                    reply_markup=_build_browse_kb(liker_telegram_id),
                )

            log.info(
                "like notification sent",
                liker=liker_telegram_id,
                liked=liked_telegram_id,
            )
        except Exception:
            log.exception("failed to process like.received event")

    async def _get_username(self, telegram_id: int) -> str | None:
        try:
            chat = await self._bot.get_chat(telegram_id)
            if chat.username:
                return f"@{chat.username}"
        except Exception:
            log.debug("failed to resolve username", telegram_id=telegram_id)
            return None
        return None

    async def _on_match_created(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        """Отправляет уведомление о новом матче."""
        try:
            data = json.loads(message.body)
            user1_telegram_id = int(data["user1_telegram_id"])
            user2_telegram_id = int(data["user2_telegram_id"])

            user1_profile = await self._profile_service.get_profile(user1_telegram_id)
            user2_profile = await self._profile_service.get_profile(user2_telegram_id)

            user1_name = user1_profile.name if user1_profile else "Пользователь"
            user2_name = user2_profile.name if user2_profile else "Пользователь"

            text1 = f"🎉 У тебя новый матч с {user2_name}!\n\nНапиши первым — не упусти момент!"
            text2 = f"🎉 У тебя новый матч с {user1_name}!\n\nНапиши первым — не упусти момент!"

            for user_id, text in [(user1_telegram_id, text1), (user2_telegram_id, text2)]:
                try:
                    await self._bot.send_message(chat_id=user_id, text=text)
                    log.info("match notification sent", user_id=user_id)
                except Exception:
                    log.warning(
                        "failed to send match notification (user may have blocked bot)",
                        user_id=user_id,
                    )

            log.info(
                "match notifications processed",
                user1=user1_telegram_id,
                user2=user2_telegram_id,
            )
        except Exception:
            log.exception("failed to process match.created event")
