"""SQLAlchemy async database configuration for the auth_service.

This module exposes the async engine, session factory and a dependency
provider for FastAPI endpoints. The configuration expects the
``DATABASE_URL`` environment variable to be set and will raise an error if
it is missing to fail fast during application startup.
"""

from __future__ import annotations

import os
from typing import AsyncGenerator, Optional

from sqlalchemy import orm
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_ENV_KEY = "DATABASE_URL"
database_url: Optional[str] = os.getenv(DATABASE_ENV_KEY)

engine = create_async_engine(database_url, echo=True)

AsyncSessionLocal: sessionmaker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = orm.declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an asynchronous database session.

    Sessions are created from :data:`AsyncSessionLocal`. Using a dependency
    ensures proper lifecycle management of the session for each request.
    """
    async with AsyncSessionLocal() as session:
        yield session
