from __future__ import annotations

import os
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import HTTPException
import jwt

load_dotenv()

_ENV_SECRET = "SECRET_KEY"
_ENV_ALG = "ALGORITHM"

SECRET_KEY = os.getenv(_ENV_SECRET)
ALGORITHM = os.getenv(_ENV_ALG)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode a JWT access token and return its payload.

    Raises HTTPException with 401 status on invalid or expired tokens.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(token: str) -> str:
    """Extract current username (``sub``) from token payload.

    Raises HTTPException(401) if subject is missing.
    """
    decoded = decode_access_token(token)
    username = decoded.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username
