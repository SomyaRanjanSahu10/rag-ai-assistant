"""
Security Utilities
==================
JWT token creation/validation + bcrypt password hashing.

Token Strategy:
- Access token: short-lived (30 min), used for API requests
- Refresh token: long-lived (7 days), used to issue new access tokens
- Both stored as HttpOnly cookies (CSRF-safe) OR in Authorization header

Why bcrypt?
- Designed specifically for passwords (slow by design)
- Automatically salts hashes (prevents rainbow table attacks)
- Work factor can be increased as hardware improves
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE-THIS-IN-PRODUCTION-use-openssl-rand-hex-32")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# bcrypt context with 12 rounds (good balance of security vs speed ~200ms/hash)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


# ── Password Hashing ───────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Tokens ─────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.
    
    Args:
        data: Payload dict (should include 'sub' = user_id)
        expires_delta: Custom expiry (defaults to ACCESS_TOKEN_EXPIRE_MINUTES)
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a long-lived refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    
    Raises:
        JWTError: If token is invalid, expired, or tampered with
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    Verify token and extract user_id (sub claim).
    Returns None if invalid instead of raising.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != token_type:
            return None
        user_id: str = payload.get("sub")
        return user_id
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None
