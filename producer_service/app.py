"""Producer Service: FastAPI application to submit reviews to Kafka.

This service exposes an endpoint to accept review text from authenticated users
and sends the data to the Kafka topic `raw_reviews` for downstream ML processing.
"""

import os
from fastapi import FastAPI, Depends
from schemas import ReviewRequest
from kafka_producer import send_to_kafka, get_kafka_producer, producer
from security import get_current_user
import logging
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    root_path=os.getenv("ROOT_PATH", ""),
    title="Producer Service",
    docs_url="/docs",
    openapi_url="/openapi.json",
)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize Kafka producer at application startup."""
    await get_kafka_producer()


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint returning the service status."""
    return {"status": "ok"}


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Gracefully stop Kafka producer at application shutdown."""
    if producer:
        await producer.stop()


@app.post("/submit-review/")
async def submit_review(
    review: ReviewRequest, username: str = Depends(get_current_user)
) -> dict:
    """Submit a review to the Kafka topic `raw_reviews`.

    Args:
        review: ReviewRequest object containing `review_text`.
        username: Authenticated username injected via dependency.

    Returns:
        dict: Confirmation including review ID and original text.
    """
    message_data = {"text": review.review_text, "username": username}
    review_id = await send_to_kafka("raw_reviews", message_data)
    logger.info("Review sent to Kafka: %s", review_id)

    return {
        "status": "Review sent to Kafka",
        "review_id": review_id,
        "review_text": review.review_text,
    }
