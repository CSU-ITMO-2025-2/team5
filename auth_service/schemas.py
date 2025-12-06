"""Pydantic schemas for request and response models used in the auth_service.

Includes models for user creation, authentication, and token responses.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    """Schema for user registration requests."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    username: str
    password: str


class UserLogin(BaseModel):
    """Schema for user login requests."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    username: str
    password: str


class Token(BaseModel):
    """Schema returned after successful authentication."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    access_token: str
    token_type: str
