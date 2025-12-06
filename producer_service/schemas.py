"""Pydantic models for Producer Service."""

from pydantic import BaseModel


class ReviewRequest(BaseModel):
    """Schema for submitting a review."""

    review_text: str
