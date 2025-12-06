"""Security helpers: password hashing, verification and JWT creation.

The module provides thin wrappers around :class:`passlib.context.CryptContext`
for Argon2 hashing and :mod:`jwt` for token encoding. Environment variables
`SECRET_KEY`, `ALGORITHM` and `ACCESS_TOKEN_EXPIRE_MINUTES` are required and
validated at import time to fail fast on misconfiguration.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from passlib.context import CryptContext
import jwt

load_dotenv()

ENV_SECRET_KEY = "SECRET_KEY"
ENV_ALGORITHM = "ALGORITHM"
ENV_ACCESS_EXPIRE = "ACCESS_TOKEN_EXPIRE_MINUTES"

SECRET_KEY = os.getenv(ENV_SECRET_KEY)
ALGORITHM = os.getenv(ENV_ALGORITHM)
_access_exp = os.getenv(ENV_ACCESS_EXPIRE)

if not SECRET_KEY or not ALGORITHM or not _access_exp:
    raise ValueError(
        "SECRET_KEY, ALGORITHM and ACCESS_TOKEN_EXPIRE_MINUTES must be set in the environment"
    )

try:
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(_access_exp)
except ValueError as exc:
    raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be an integer") from exc

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def _normalize_password(password: str) -> str:
    """Normalize and truncate password to the hashing library limits."""
    return password.strip()[:72]


def get_password_hash(password: str) -> str:
    """Return a secure hash for ``password``.

    The function normalizes the password (strips whitespace and truncates to
    72 characters) before hashing to ensure consistent results between
    registration and verification.
    """
    normalized = _normalize_password(password)
    return pwd_context.hash(normalized)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that ``plain_password`` matches ``hashed_password``.

    The same normalization used during hashing is applied before verification
    to avoid mismatches caused by leading/trailing whitespace.
    """
    normalized = _normalize_password(plain_password)
    return pwd_context.verify(normalized, hashed_password)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token containing ``data`` and an expiry.

    If ``expires_delta`` is not provided, the module-level
    ``ACCESS_TOKEN_EXPIRE_MINUTES`` value is used. The returned token is a
    URL-safe string produced by :func:`jwt.encode`.
    """
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
