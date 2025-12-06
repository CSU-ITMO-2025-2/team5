"""ML service application.

This module implements a FastAPI application which consumes raw reviews from
Kafka, performs emotion detection with a Hugging Face transformer model, writes
results to the database and republishes processed messages. The model used is
``cointegrated/rubert-tiny2-cedr-emotion-detection`` (multi-label emotion
classification).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from transformers import pipeline
from database import engine, AsyncSessionLocal
from db_core import Base
from models import ReviewResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", "my-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092"
)
TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "raw_reviews")
TOPIC_PROCESSED = os.getenv("KAFKA_TOPIC_PROCESSED", "processed_reviews")
MODEL_NAME = os.getenv(
    "MODEL_NAME", "seara/rubert-base-cased-russian-emotion-detection-ru-go-emotions"
)

producer: Optional[AIOKafkaProducer] = None
sentiment_pipeline: Optional[Any] = None


def _load_model_sync(model_name: str) -> Any:
    """Synchronous model loader used inside a thread pool.

    The function uses the Transformers pipeline for text classification and
    requests all scores to support multi-label outputs.
    """
    return pipeline(
        "text-classification",
        model=model_name,
        tokenizer=model_name,
        return_all_scores=True,
    )


async def load_model_async(model_name: str) -> Any:
    """Load the transformer model asynchronously using a thread executor.

    Loading heavy model artifacts is performed in a background thread to avoid
    blocking the event loop during application startup.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _load_model_sync, model_name)


def _select_top_label_from_scores(scores: Any) -> Dict[str, float]:
    """Convert pipeline scores into a label->score mapping and select top.

    The transformers pipeline returns a list of dicts when ``return_all_scores``
    is enabled. This helper normalizes that output into a mapping and returns
    the label with the maximum score.
    """
    if not scores:
        return {"neutral": 0.0}

    if isinstance(scores, list) and len(scores) and isinstance(scores[0], list):
        entries = scores[0]
    else:
        entries = scores

    label_scores = {entry["label"].lower(): float(entry["score"]) for entry in entries}
    top_label = max(label_scores, key=label_scores.get)
    return {top_label: label_scores[top_label]}


async def get_kafka_producer_with_retry(
    retries: int = 5, delay: int = 2
) -> AIOKafkaProducer:
    """Create and start an AIOKafkaProducer with retries."""
    for attempt in range(1, retries + 1):
        try:
            prod = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await prod.start()
            logger.info("Kafka Producer connected.")
            return prod
        except Exception as exc:
            logger.warning(
                "Kafka connection failed (attempt %d/%d): %s", attempt, retries, exc
            )
            await asyncio.sleep(delay)
    raise ConnectionError("Could not connect to Kafka after retries")


async def process_message(msg_value: bytes) -> None:
    """Process a single Kafka message: run inference, persist and forward result."""
    try:
        data = json.loads(msg_value.decode("utf-8"))
        review_text = data.get("text", "")
        review_id = data.get("id")

        loop = asyncio.get_running_loop()
        sentiment_raw = await loop.run_in_executor(
            None, sentiment_pipeline, review_text
        )

        top = _select_top_label_from_scores(sentiment_raw)
        sentiment, score = next(iter(top.items()))

        async with AsyncSessionLocal() as session:
            new_review = ReviewResult(
                review_id=review_id,
                review_text=review_text,
                sentiment=sentiment,
                polarity=str(round(score, 4)),
                author=data.get("username", "anonymous"),
            )
            session.add(new_review)
            await session.commit()

        if producer:
            processed_data = {
                "review_id": review_id,
                "sentiment": sentiment,
                "user": data.get("username"),
                "text": review_text,
            }
            await producer.send_and_wait(TOPIC_PROCESSED, processed_data)

        logger.info("Analyzed review %s: %s (score: %.2f)", review_id, sentiment, score)
    except Exception as exc:
        logger.error("Error processing message: %s", exc)


async def consume_loop() -> None:
    """Continuously consume messages from Kafka and process them."""
    while True:
        try:
            consumer = AIOKafkaConsumer(
                TOPIC_RAW,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id="ml-service-group",
                auto_offset_reset="earliest",
            )
            await consumer.start()
            logger.info("ML Consumer started.")
            async for msg in consumer:
                await process_message(msg.value)
        except Exception as exc:
            logger.error("Consumer crashed: %s. Restarting in 5s...", exc)
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        logger.error("DB Init failed: %s", exc)

    global sentiment_pipeline
    sentiment_pipeline = await load_model_async(MODEL_NAME)

    global producer
    try:
        producer = await get_kafka_producer_with_retry()
    except Exception as exc:
        logger.error("Critical Kafka Error: %s", exc)

    asyncio.create_task(consume_loop())

    yield

    if producer:
        await producer.stop()


app = FastAPI(
    root_path="/producer",
    title="ML Service",
    lifespan=lifespan,
    docs_url="/ml/docs",
    openapi_url="/openapi.json",
)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    status = "alive" if sentiment_pipeline else "loading_model"
    return {"status": status}
