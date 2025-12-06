"""JWT-based security utilities for Producer Service.

Provides token decoding and current user extraction. Raises FastAPI HTTPExceptions
for invalid or expired tokens.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import HTTPException
import jwt


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

if not SECRET_KEY or not ALGORITHM:
    raise ValueError("SECRET_KEY and ALGORITHM must be set in environment variables")


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode JWT access token and return the payload.

    Raises:
        HTTPException: If token is expired or invalid.

    Returns:
        dict: Payload of the decoded token.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(token: str) -> str:
    """Extract current username from decoded JWT token.

    Raises:
        HTTPException: If the 'sub' field is missing.

    Returns:
        str: Username from token payload.
    """
    decoded_token = decode_access_token(token)
    username: str = decoded_token.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username
