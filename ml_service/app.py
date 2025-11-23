from fastapi import FastAPI, Depends
from security import get_current_user
from kafka_consumer import consume_from_kafka
from schemas import TimeoutRequest, ReviewResponse, ReviewsListResponse

app = FastAPI(
    docs_url="/ml/docs",
    openapi_url="/openapi.json"
)

@app.post("/analyze-sentiment/", response_model=ReviewsListResponse)
async def analyze_sentiment(timeout: TimeoutRequest, token: str = Depends(get_current_user)) -> ReviewsListResponse:
    resp = []
    kafka = await consume_from_kafka(timeout=timeout.timeout)
    sentiment = "positive"
    
    for queue in kafka:
        resp.append(ReviewResponse(review_text=queue, sentiment=sentiment))
    
    return ReviewsListResponse(reviews=resp)
