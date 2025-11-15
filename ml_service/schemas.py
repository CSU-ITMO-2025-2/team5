from pydantic import BaseModel
from typing import List

class ReviewResponse(BaseModel):
    review_text: str
    sentiment: str

class ReviewsListResponse(BaseModel):
    reviews: List[ReviewResponse]

class TimeoutRequest(BaseModel):
    timeout: int