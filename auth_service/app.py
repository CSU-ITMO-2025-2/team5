"""Authentication FastAPI application for the auth_service.

This module exposes two endpoints used by other services and clients:

- ``POST /register/`` — register a new user; returns a simple success
  message on creation.
- ``POST /login/`` — authenticate a user and return a JSON Web Token
  (JWT) in the response body.

The implementation relies on an asynchronous SQLAlchemy session provided by
``get_db`` and keeps business rules intentionally minimal: unique username
check, password hashing, and token creation.
"""

from __future__ import annotations

import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict

from database import get_db
from models import User
from schemas import Token, UserCreate, UserLogin
from security import (
    create_access_token,
    get_password_hash,
    verify_password,
)

app = FastAPI(
    root_path=os.getenv("ROOT_PATH", ""), docs_url="/docs", openapi_url="/openapi.json"
)


@app.post("/register/")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)) -> dict:
    """Register a new user.

    Ensures the username is not already present, hashes the provided
    password and persists a new ``User`` record.
    """
    stmt = select(User).filter(User.username == user.username)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()

    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)

    db.add(new_user)
    await db.commit()

    return {"msg": "User created successfully"}


@app.post("/login/", response_model=Token)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)) -> Token:
    """Authenticate user and return an access token.

    Validates credentials and returns a bearer token on success.
    """
    stmt = select(User).filter(User.username == user.username)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint returning the service status."""
    return {"status": "ok"}
