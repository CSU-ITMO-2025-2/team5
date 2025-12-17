# pylint: disable=not-callable
"""ORM models for the ml_service application."""

from __future__ import annotations
from sqlalchemy import Column, DateTime, Integer, String, Text, func, Float
from db_core import Base


class ReviewResult(Base):
    """ORM model representing processed review results.

    Fields mirror the database schema used by migrations and by the
    ML processing pipeline.
    """

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(String(255), unique=True, index=True, nullable=True)
    review_text = Column(Text, nullable=False)
    sentiment = Column(String(50), nullable=False)
    score = Column(Float, nullable=False)
    reply = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ReviewResult id={self.id!r} review_id={self.review_id!r} sentiment={self.sentiment!r}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "review_id": self.review_id,
            "review_text": self.review_text,
            "sentiment": self.sentiment,
            "score": self.score,
            "reply": self.reply,
            "author": self.author,
            "created_at": (
                self.created_at.isoformat() if self.created_at is not None else None
            ),
        }
