"""
Auth Dependencies
=================
FastAPI dependency functions for extracting and validating
the current user from JWT tokens in request headers or cookies.
"""

import logging
from fastapi import Depends, HTTPException, Header, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from database import get_db
from models.user import User
from utils.security import verify_token
from utils.errors import AuthError

logger = logging.getLogger(__name__)

# Bearer token extractor (reads Authorization: Bearer <token>)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract user from JWT Bearer token.
    Raises 401 if token missing, invalid, or user not found.
    """
    if not credentials:
        raise AuthError("No authentication token provided")

    user_id = verify_token(credentials.credentials, token_type="access")
    if not user_id:
        raise AuthError("Invalid or expired access token")

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthError("User not found or deactivated")

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of raising on missing token."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except AuthError:
        return None
