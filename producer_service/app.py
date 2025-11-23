from fastapi import FastAPI, Depends
from schemas import ReviewRequest
from kafka_producer import send_to_kafka
from security import get_current_user

app = FastAPI(
    docs_url="/producer/docs",
    openapi_url="/producer/openapi.json",
    servers=[{"url": "/producer"}]
)

@app.post("/submit-review/")
async def submit_review(review: ReviewRequest, token: str = Depends(get_current_user)):
    review_text = review.review_text
    await send_to_kafka('raw_reviews', {'review_text': review_text})
    return {"status": "Review sent to Kafka", "review_text": review_text}
