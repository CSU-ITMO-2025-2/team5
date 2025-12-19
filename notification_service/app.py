"""Notification service: consume processed reviews and send alerts.

This FastAPI application listens to the ``processed_reviews`` Kafka topic,
maps detected emotions to a coarse sentiment and a Russian label, and sends
notifications to a configured Telegram chat. The module is intentionally
concise: errors during notification are logged and do not stop the consumer.
Emojis are preserved in messages for visual priority.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict

from contextlib import asynccontextmanager
from fastapi import FastAPI
from aiokafka import AIOKafkaConsumer
import httpx

from datetime import datetime
from dateutil import parser
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from db import init_db, add_subscriber, get_all_subscribers


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "my-cluster-kafka-bootstrap.team5-ns.svc.cluster.local:9092",
)
TOPIC_PROCESSED = os.getenv("KAFKA_TOPIC_PROCESSED", "processed-reviews")

KAFKA_USERNAME = os.getenv("KAFKA_USERNAME")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "notification-group")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    if TELEGRAM_BOT_TOKEN
    else None
)


bot = Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None
dp = Dispatcher()


@dp.message(CommandStart())
async def handle_start(message: types.Message):
    """Handles new users starting a chat with the bot."""
    chat_id = message.chat.id
    await add_subscriber(chat_id)
    await message.answer("Вы успешно подписались на уведомления о sentiment-анализе!")


def _load_json_mapping(file_path: str) -> Dict[str, str]:
    """Load a JSON file and return a string-to-string mapping.

    Returns an empty dictionary if the file is missing or invalid.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error("Mapping file not found: %s", file_path)
        return {}

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
            logger.error("Mapping file %s does not contain a JSON object", file_path)
            return {}
    except Exception as exc:
        logger.error("Failed to load mapping %s: %s", file_path, exc)
        return {}


EMOTION_MAPPING = _load_json_mapping("mapping/emotion_to_sentiment.json")
EMOTION_TRANSLATE = _load_json_mapping("mapping/emotion_to_russian.json")


async def _send_telegram(chat_id: int, message: str) -> None:
    """Send a Markdown-formatted message to a specific Telegram chat_id."""
    if not TELEGRAM_API_URL:
        return

    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(TELEGRAM_API_URL, json=payload, timeout=5)
            if resp.is_success:
                logger.debug(
                    "Telegram notification sent to %s (status=%s)",
                    chat_id,
                    resp.status_code,
                )
            else:
                resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Telegram HTTP error for chat_id %s: %s - %s",
            chat_id,
            exc.response.status_code,
            exc.response.text,
        )
    except Exception as exc:
        logger.error("Failed to send telegram message to %s: %s", chat_id, exc)


def process_message(msg_value: bytes) -> str | None:
    """Process a single Kafka message and send a Telegram notification if required.

    The function maps the model emotion to a sentiment and a Russian label,
    chooses an emoji and sends a formatted message. Errors are logged but do
    not raise.
    """
    try:
        payload = json.loads(msg_value.decode("utf-8"))
    except Exception as exc:
        logger.error("Failed to decode message: %s", exc)
        return None

    review_id = payload.get("review_id")
    user = payload.get("user") or "Anonymous"
    emotion = payload.get("sentiment") or "neutral"
    text = payload.get("text") or ""
    reply_template = payload.get("reply") or "Нет рекомендации"

    created_at_str = payload.get("created_at")
    created_at_formatted = "-"
    if created_at_str:
        try:
            dt_object = parser.isoparse(created_at_str)
            created_at_formatted = dt_object.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            logger.warning("Could not parse created_at: %s", created_at_str)
            created_at_formatted = created_at_str

    sentiment = EMOTION_MAPPING.get(emotion, "нейтральная")
    emotion_ru = EMOTION_TRANSLATE.get(emotion, emotion)

    if sentiment == "негативная":
        emoji = "🔴"
    elif sentiment == "позитивная":
        emoji = "🟢"
    else:
        emoji = "🟡"

    short_id = None
    if isinstance(review_id, str) and len(review_id) >= 8:
        short_id = f"{review_id[:8]}..."
    elif review_id is not None:
        short_id = str(review_id)
    else:
        short_id = "-"

    message = (
        f"{emoji} *НОВЫЙ ОТЗЫВ* {emoji}\n"
        f"Пользователь: `{user}`\n"
        f"ID отзыва: `{short_id}`\n"
        f"Создан: `{created_at_formatted}`\n"
        f"Отзыв: `{text}`\n"
        f"Эмоция: **{emotion_ru.upper()}**\n"
        f"Рекомендуемый ответ:\n`{reply_template}`"
    )

    return message


async def _consume_loop() -> None:
    """Continuously consume messages from Kafka and broadcast them to subscribers."""
    while True:
        consumer = None
        try:
            consumer_config = {
                "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
                "group_id": KAFKA_GROUP_ID,
                "auto_offset_reset": "earliest",
            }
            if KAFKA_USERNAME and KAFKA_PASSWORD:
                consumer_config.update(
                    {
                        "sasl_mechanism": "SCRAM-SHA-512",
                        "security_protocol": "SASL_PLAINTEXT",
                        "sasl_plain_username": KAFKA_USERNAME,
                        "sasl_plain_password": KAFKA_PASSWORD,
                    }
                )
            consumer = AIOKafkaConsumer(TOPIC_PROCESSED, **consumer_config)
            await consumer.start()
            logger.info("Notification consumer started. Waiting for messages...")

            async for msg in consumer:
                logger.info(
                    f"Received message from Kafka: offset={msg.offset}, value={msg.value}"
                )

                message_text = None
                try:
                    message_text = process_message(msg.value)
                    logger.info(f"Processed message content: '{message_text}'")
                except Exception as e:
                    logger.error(
                        f"Failed to process message with offset {msg.offset}: {e}",
                        exc_info=True,
                    )
                    continue
                if not message_text:
                    logger.warning(
                        f"Message with offset {msg.offset} resulted in empty text. Skipping."
                    )
                    continue
                subscribers = await get_all_subscribers()
                logger.info(f"Found {len(subscribers)} subscribers.")
                if not subscribers:
                    logger.warning(
                        "No subscribers to send notification to. Skipping broadcast."
                    )
                    continue

                logger.info("Broadcasting message to %d subscribers", len(subscribers))
                tasks = [
                    _send_telegram(chat_id, message_text) for chat_id in subscribers
                ]
                await asyncio.gather(*tasks)
                logger.info("Broadcast finished successfully.")

        except Exception as exc:
            logger.error("Consumer CRASHED: %s. Retrying in 5s...", exc, exc_info=True)
            if consumer:
                await consumer.stop()
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the startup and shutdown of background tasks."""
    await init_db()

    consumer_task = asyncio.create_task(_consume_loop())

    polling_task = None
    if bot:
        polling_task = asyncio.create_task(dp.start_polling(bot))
        logger.info("Telegram bot polling started")

    try:
        yield
    finally:
        consumer_task.cancel()
        if polling_task:
            await dp.storage.close()
            await bot.session.close()
            polling_task.cancel()

        try:
            await consumer_task
        except asyncio.CancelledError:
            logger.info("Notification consumer task cancelled")
        if polling_task:
            try:
                await polling_task
            except asyncio.CancelledError:
                logger.info("Telegram polling task cancelled")


app = FastAPI(
    root_path=os.getenv("ROOT_PATH", ""),
    title="Notify Service",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint returning the service status."""
    return {"status": "ok"}
