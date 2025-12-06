"""Utilities to consume messages from Kafka for ml_service."""

from __future__ import annotations

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List

from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", "my-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092"
)
TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "raw_reviews")


async def consume_from_kafka(timeout: int = 5) -> List[str]:
    """Collect messages from Kafka for a limited time window.

    The function starts a consumer, collects messages for up to ``timeout``
    seconds and returns a list of decoded message payloads.
    """
    consumer = AIOKafkaConsumer(
        TOPIC_RAW,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="ml-service-consumer",
    )

    messages: List[str] = []
    start_time = datetime.utcnow()

    await consumer.start()
    try:
        logger.info("Kafka consumer started")
        while True:
            elapsed = datetime.utcnow() - start_time
            if elapsed >= timedelta(seconds=timeout):
                break

            try:
                msg = await asyncio.wait_for(consumer.getone(), timeout=timeout)
            except asyncio.TimeoutError:
                continue

            if msg is not None and msg.value is not None:
                try:
                    messages.append(msg.value.decode())
                except Exception as exc:
                    logger.warning("Failed to decode message: %s", exc)
    except Exception as exc:
        logger.error("Error while consuming messages: %s", exc)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")

    logger.info("Messages collected in %d seconds: %d", timeout, len(messages))
    return messages
