from pydantic import BaseModel

class ReviewRequest(BaseModel):
    review_text: str
