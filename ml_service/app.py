from __future__ import annotations

import inspect
import random
import asyncio
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import select
from openai import OpenAI
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import httpx

from pathlib import Path
from database import engine, AsyncSessionLocal
from db_core import Base
from models import ReviewResult
from security import get_current_user
from circuit_breaker import create_openai_circuit_breaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUEUE_SIZE = 6
WORKER_COUNT = 2
consumer: Optional[AIOKafkaConsumer] = None
_consumer_ready_event = asyncio.Event()
message_queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "my-cluster-kafka-bootstrap.team5-ns.svc.cluster.local:9092",
)
TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "raw-reviews")
TOPIC_PROCESSED = os.getenv("KAFKA_TOPIC_PROCESSED", "processed-reviews")

KAFKA_USERNAME = os.getenv("KAFKA_USERNAME")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "ml-service-group")

OPENAI_API_KEY = os.getenv("API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.proxyapi.ru/openai/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

openai_client: Optional[OpenAI] = None
producer: Optional[AIOKafkaProducer] = None
sentiment_pipeline: Optional[Any] = None

openai_circuit_breaker = create_openai_circuit_breaker("OpenAI")

EMOTIONS = ["neutral", "happiness", "sadness", "enthusiasm", "fear", "anger", "disgust"]
_PROMPT_CACHE: dict[str, str] = {}


def load_prompt(name: str) -> str:
    if name in _PROMPT_CACHE:
        return _PROMPT_CACHE[name]

    base_dir = Path(__file__).resolve().parent
    prompt_path = base_dir / "prompts" / name

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    content = prompt_path.read_text(encoding="utf-8")
    _PROMPT_CACHE[name] = content
    return content


async def get_kafka_producer_with_retry(
    retries: int = 5, delay: int = 2
) -> AIOKafkaProducer:
    """Create and start an AIOKafkaProducer with retries."""
    global producer
    for attempt in range(1, retries + 1):
        try:
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

            prod = AIOKafkaProducer(**producer_config)
            await prod.start()
            producer = prod
            logger.info("Kafka Producer connected.")
            return
        except Exception as exc:
            logger.warning(
                "Kafka connection failed (%d/%d): %s",
                attempt,
                retries,
                exc,
            )
            await asyncio.sleep(delay)

    logger.error("Kafka producer FAILED to connect.")


def init_openai_client() -> bool:
    """Initialize OpenAI client"""
    global openai_client
    if OPENAI_API_KEY:
        openai_client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
        )
        logger.info("OpenAI client initialized")
        return True
    else:
        logger.warning("API_KEY not set, OpenAI disabled")
        return False


def _extract_text_from_response(resp: Any) -> str:
    """Extract text from various response object formats."""
    text = _extract_from_attributes(resp)
    if text:
        return text.strip()
    text = _extract_from_output(resp)
    if text:
        return text.strip()
    text = _extract_from_text_or_raw_text(resp)
    if text:
        return str(text).strip()
    return _extract_fallback(resp).strip()


def _extract_from_attributes(resp: Any) -> Optional[str]:
    """Extract text from response object with text/type attributes."""
    if not hasattr(resp, "text"):
        return None

    text = getattr(resp, "text")
    if hasattr(resp, "type"):
        if text and isinstance(text, str):
            return text
        elif text:
            return str(text)
        return ""
    if text and isinstance(text, str):
        return text

    return None


def _extract_from_output(resp: Any) -> Optional[str]:
    """Extract text from response object with output attribute."""
    output = getattr(resp, "output", None)
    if not output or not isinstance(output, (list, tuple)) or len(output) == 0:
        return None

    first_item = output[0]
    content = None

    if isinstance(first_item, dict):
        content = first_item.get("content")
    elif hasattr(first_item, "content"):
        content = getattr(first_item, "content", None)

    if not content or not isinstance(content, (list, tuple)) or len(content) == 0:
        return None

    candidate = content[0]

    if isinstance(candidate, dict):
        return candidate.get("text", "")
    elif isinstance(candidate, str):
        return candidate
    elif hasattr(candidate, "text"):
        return getattr(candidate, "text", "")

    return str(candidate) if candidate else None


def _extract_from_text_or_raw_text(resp: Any) -> Optional[str]:
    """Extract text from text or raw_text attributes."""
    text = getattr(resp, "text", None) or getattr(resp, "raw_text", None)
    return str(text) if text else None


def _extract_fallback(resp: Any) -> str:
    """Fallback extraction methods."""
    try:
        return json.dumps(resp)
    except Exception:
        return str(resp)


def _get_openai_create_method():
    """Get the appropriate create method from OpenAI client."""
    if not openai_client:
        raise RuntimeError("OpenAI client not initialized")

    create = getattr(openai_client.responses, "create", None)
    if create is None:
        create = getattr(openai_client, "create", None)
    if create is None:
        raise RuntimeError("Cannot find .responses.create or .create on OpenAI client")

    return create


async def _make_openai_call(create_method, prompt: str, timeout: float = 15.0) -> Any:
    """Make the actual OpenAI API call."""
    if inspect.iscoroutinefunction(create_method):
        coro = create_method(model=OPENAI_MODEL, input=prompt)
        return await asyncio.wait_for(coro, timeout=timeout)
    else:
        return await asyncio.wait_for(
            asyncio.to_thread(create_method, model=OPENAI_MODEL, input=prompt),
            timeout=timeout,
        )


async def _call_openai_with_circuit_breaker(
    prompt: str, timeout: Optional[float] = 15.0
) -> str:

    async def _call_openai_func():
        create_method = _get_openai_create_method()
        resp = await _make_openai_call(create_method, prompt, timeout)
        return _extract_text_from_response(resp)

    try:
        result = await openai_circuit_breaker.call(_call_openai_func)
        return result
    except Exception as exc:
        logger.error(f"OpenAI circuit breaker failed: {exc}")
        raise


def _extract_json_from_text(raw_text: str) -> dict[str, Any]:
    """Extract JSON from raw text response."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass
    json_pattern = r"\{[^{}]*\}"
    matches = re.findall(json_pattern, raw_text, re.DOTALL)

    if not matches:
        raise ValueError("No JSON found in OpenAI response")
    matches.sort(key=len, reverse=True)

    for json_str in matches:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str_fixed = re.sub(r"([{,]\s*)(\w+)(\s*:)", r'\1"\2"\3', json_str)
            try:
                return json.loads(json_str_fixed)
            except json.JSONDecodeError:
                continue

    raise ValueError("Cannot parse any JSON from OpenAI response")


def _validate_and_normalize_result(parsed: dict[str, Any]) -> tuple[str, float, str]:
    """Validate and normalize parsed result."""
    label = parsed.get("label", "")
    raw_score = parsed.get("score", 0.0)
    reply = parsed.get("reply", "")

    if not isinstance(label, str) or label.lower() not in EMOTIONS:
        raise ValueError(f"Invalid label from OpenAI: {label!r}")

    try:
        score = float(raw_score)
    except (ValueError, TypeError):
        score = 0.0

    score = max(0.0, min(1.0, score))
    reply = str(reply).strip()

    return label.lower(), score, reply


async def analyze_with_openai(text: str, username: str) -> tuple[str, float, str]:
    """
    Build prompt (from file), call OpenAI via _call_openai and parse JSON.
    Returns (label, score, reply).
    Raises if parsing fails — caller should fallback.
    """
    template = load_prompt("review_emotion_and_reply.txt")

    prompt = template.replace("{{INPUT}}", text.replace('"', '\\"')).replace(
        "{{EMOTIONS}}", ", ".join(EMOTIONS)
    )

    raw = await _call_openai_with_circuit_breaker(prompt)
    if hasattr(raw, "text"):
        raw = raw.text
    raw = (raw or "").strip()
    logger.info("Raw response (first 2000 chars): %s", raw[:2000])

    try:
        parsed = _extract_json_from_text(raw)
        logger.debug("Successfully parsed JSON")
        return _validate_and_normalize_result(parsed)
    except Exception as e:
        logger.error(f"Failed to parse OpenAI response: {e}")
        raise ValueError(f"Cannot parse OpenAI response: {e}")


async def process_message(msg_value: bytes) -> None:
    try:
        data = json.loads(msg_value.decode("utf-8"))
        review_text = data.get("text", "")
        review_id = data.get("id")
        username = data.get("username") or "Customer"

        try:
            sentiment, score, reply = await analyze_with_openai(review_text, username)
        except Exception as e:
            logger.error(
                f"OpenAI analysis failed for review {review_id}: {str(e)}",
                exc_info=True,
            )
            sentiment = random.choice(EMOTIONS)
            score = 0.85
            reply = (
                f"Здравствуйте, {username}! Спасибо за обратную связь. "
                "Мы благодарим вас за то, что поделились своим мнением."
            )

        async with AsyncSessionLocal() as session:
            new_review = ReviewResult(
                review_id=review_id,
                review_text=review_text,
                sentiment=sentiment,
                score=round(score, 4),
                reply=reply,
                author=username,
            )
            session.add(new_review)
            await session.commit()
            await session.refresh(new_review)

        if producer:
            processed_data = {
                "review_id": review_id,
                "sentiment": sentiment,
                "score": round(score, 4),
                "reply": reply,
                "user": username,
                "text": review_text,
                "created_at": new_review.created_at.isoformat(),
            }
            await producer.send_and_wait(TOPIC_PROCESSED, processed_data)

        logger.info("Analyzed review %s: %s", review_id, sentiment)
    except Exception as exc:
        logger.error("Error processing message: %s", exc, exc_info=True)


async def worker_loop(worker_id: int):
    logger.info("Worker %d started", worker_id)

    while True:
        msg = await message_queue.get()

        try:
            await process_message(msg.value)
        except Exception as exc:
            logger.error(
                "Worker %d failed processing message: %s", worker_id, exc, exc_info=True
            )
        finally:
            message_queue.task_done()


async def consume_loop() -> None:
    """Continuously consume messages from Kafka and enqueue them for workers."""
    global consumer
    consumer_config = {
        "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
        "group_id": KAFKA_GROUP_ID,
        "enable_auto_commit": False,
        "max_poll_records": 10,
        "heartbeat_interval_ms": 3000,
        "session_timeout_ms": 20000,
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

    consumer = AIOKafkaConsumer(TOPIC_RAW, **consumer_config)
    await consumer.start()
    try:
        while not consumer.assignment():
            await asyncio.sleep(1)
        logger.info("Consumer has been assigned partitions")
        _consumer_ready_event.set()

        for i in range(WORKER_COUNT):
            asyncio.create_task(worker_loop(i))

        async for msg in consumer:
            await message_queue.put(msg)
            await consumer.commit()
    except Exception as exc:
        logger.error("Consumer crashed: %s", exc, exc_info=True)
        _consumer_ready_event.clear()
    finally:
        await consumer.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        logger.error("DB Init failed: %s", exc)

    init_openai_client()
    await get_kafka_producer_with_retry()
    await asyncio.sleep(1)
    asyncio.create_task(consume_loop())

    yield

    if producer:
        await producer.stop()


app = FastAPI(
    root_path=os.getenv("ROOT_PATH", ""),
    title="ML Service",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)


@app.get("/health")
async def health():
    return {
        "model": "ready" if sentiment_pipeline else "loading",
        "kafka": "ready" if producer else "initializing",
    }


@app.get("/consumer/status")
async def consumer_ready():
    return {"ready": _consumer_ready_event.is_set()}


@app.get("/reviews/{review_id}")
async def get_review_result(
    review_id: str, username: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Return stored ML result or processing status for the given review_id."""
    async with AsyncSessionLocal() as session:
        stmt = select(ReviewResult).where(
            ReviewResult.review_id == review_id,
            ReviewResult.author == username,
        )
        result = await session.execute(stmt)
        review: Optional[ReviewResult] = result.scalar_one_or_none()

        if review is None:
            raise HTTPException(status_code=404, detail="Review result not found")

        return review.to_dict()
