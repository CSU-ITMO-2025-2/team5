"""SQLAlchemy models for the auth_service.

Only a minimal ``User`` model is defined here; it mirrors the database
schema used by Alembic migrations and the FastAPI endpoints.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Column, Integer, String

from database import Base


class User(Base):
    """ORM model representing an application user.

    Attributes
    ----------
    id:
        Integer primary key.
    username:
        Unique username used for authentication; kept nullable to match the
        existing migration semantics.
    hashed_password:
        Password hash stored as a string.
    """

    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, index=True)
    username: Optional[str] = Column(
        String(255), unique=True, index=True, nullable=True
    )
    hashed_password: Optional[str] = Column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<User id={self.id!r} username={self.username!r}>"

    def to_dict(self) -> dict:
        return {"id": self.id, "username": self.username}
