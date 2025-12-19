"""Kafka Producer utilities for Producer Service.

Provides async functions to create a Kafka producer and send messages
to a specified topic. Each review message is assigned a unique UUID.
"""

from __future__ import annotations

import uuid
import json
import logging
import os
from typing import Optional

from aiokafka import AIOKafkaProducer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "my-cluster-kafka-bootstrap.team5-ns.svc.cluster.local:9092",
)
KAFKA_USERNAME = os.getenv("KAFKA_USERNAME")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD")

producer: Optional[AIOKafkaProducer] = None


async def get_kafka_producer() -> AIOKafkaProducer:
    """Initialize or return the existing AIOKafkaProducer instance.

    Returns:
        AIOKafkaProducer: Active Kafka producer instance.
    """
    global producer
    if producer is None:
        producer_config = {
            "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
            "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
        }
        if KAFKA_USERNAME and KAFKA_PASSWORD:
            producer_config.update(
                {
                    "sasl_mechanism": "SCRAM-SHA-512",
                    "security_protocol": "SASL_PLAINTEXT",
                    "sasl_plain_username": KAFKA_USERNAME,
                    "sasl_plain_password": KAFKA_PASSWORD,
                }
            )
        producer = AIOKafkaProducer(**producer_config)
        await producer.start()
        logger.info("Kafka producer started successfully.")
    return producer


async def send_to_kafka(topic: str, data: dict) -> str:
    """Send a message containing review data to the specified Kafka topic.

    A unique UUID is generated for each review message.

    Args:
        topic (str): Kafka topic to send the message to.
        data (dict): Dictionary with keys 'text' and 'username'.

    Returns:
        str: UUID of the sent review message.
    """
    prod = await get_kafka_producer()
    review_id = str(uuid.uuid4())

    full_message = {
        "id": review_id,
        "text": data.get("text", ""),
        "username": data.get("username", "anonymous"),
    }

    await prod.send_and_wait(topic, full_message)
    logger.info("Sent review %s to Kafka topic %s", review_id, topic)
    return review_id
