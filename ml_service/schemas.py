"""Schemas for request and response models used in the ML service."""

from __future__ import annotations
from typing import List
from pydantic import BaseModel, ConfigDict


class ReviewResponse(BaseModel):
    """Single review representation returned by the ML service."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    review_text: str
    sentiment: str


class ReviewsListResponse(BaseModel):
    """Container for a list of reviews."""

    model_config = ConfigDict(extra="forbid")

    reviews: List[ReviewResponse]


class TimeoutRequest(BaseModel):
    """Request schema to control timeouts for test consumers."""

    model_config = ConfigDict(extra="forbid")

    timeout: int
