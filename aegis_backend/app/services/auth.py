"""
app/services/auth.py
JWT-based authentication for AEGIS backend.
Uses python-jose for token encoding/decoding.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

logger = logging.getLogger("aegis.auth")

# ── Configuration ──────────────────────────────────────────────
SECRET_KEY = "aegis-super-secret-key-do-not-expose"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Single hardcoded admin credential for hackathon demo
VALID_USERNAME = "admin"
VALID_PASSWORD = "aegis123"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


# ── Token Creation ─────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ── User Authentication ────────────────────────────────────────

def authenticate_user(username: str, password: str) -> Optional[str]:
    """
    Validate credentials against hardcoded admin account.
    Returns the username string on success, None on failure.
    """
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        return username
    return None


# ── Token Validation Dependency ────────────────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    FastAPI dependency: decodes and validates Bearer JWT.
    Raises 401 if token is missing, expired, or malformed.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username
