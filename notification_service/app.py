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


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", "my-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092"
)
TOPIC_PROCESSED = os.getenv("KAFKA_TOPIC_PROCESSED", "processed_reviews")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage" if TELEGRAM_BOT_TOKEN else None
)


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


async def _send_telegram(message: str) -> None:
    """Send a Markdown-formatted message to the configured Telegram chat.

    If the bot token or chat id is not configured the function logs a warning
    and returns silently.
    """
    if not TELEGRAM_API_URL or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram token or chat id not configured; skipping notification")
        return

    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(TELEGRAM_API_URL, json=payload, timeout=5)
            resp.raise_for_status()
            logger.info("Telegram notification sent (status=%s)", resp.status_code)
    except httpx.HTTPStatusError as exc:
        logger.error("Telegram HTTP error: %s - %s", exc.response.status_code, exc.response.text)
    except Exception as exc:
        logger.error("Failed to send telegram message: %s", exc)


async def process_message(msg_value: bytes) -> None:
    """Process a single Kafka message and send a Telegram notification if required.

    The function maps the model emotion to a sentiment and a Russian label,
    chooses an emoji and sends a formatted message. Errors are logged but do
    not raise.
    """
    try:
        payload = json.loads(msg_value.decode("utf-8"))
    except Exception as exc:
        logger.error("Failed to decode message: %s", exc)
        return

    review_id = payload.get("review_id")
    user = payload.get("user") or "Anonymous"
    emotion = payload.get("sentiment") or "neutral"
    text = payload.get("text") or ""

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
        f"{emoji} *NEW REVIEW ALERT* {emoji}\n"
        f"User: `{user}`\n"
        f"ID: `{short_id}`\n"
        f"Message: `{text}`\n"
        f"Emotion: **{emotion_ru.upper()}**"
    )

    await _send_telegram(message)


async def _consume_loop() -> None:
    """Continuously consume messages from Kafka and process them."""
    while True:
        try:
            consumer = AIOKafkaConsumer(
                TOPIC_PROCESSED,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id="notification-group",
                auto_offset_reset="latest",
            )
            await consumer.start()
            logger.info("Notification consumer started")
            async for msg in consumer:
                await process_message(msg.value)
        except Exception as exc:
            logger.error("Consumer crashed: %s. Retrying in 5s...", exc)
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_consume_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Notification consumer task cancelled")


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
