"""Async SQLAlchemy engine and session factory for ml_service."""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

ENV_DATABASE = "DATABASE_URL"


database_url: Optional[str] = os.getenv(ENV_DATABASE)
if not database_url:
    raise ValueError(f"{ENV_DATABASE} is not set in the environment variables")

engine = create_async_engine(database_url, echo=False)

AsyncSessionLocal: sessionmaker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
