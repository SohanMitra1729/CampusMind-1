"""
app/core/security.py — Authentication & Authorization dependencies for FastAPI
─────────────────────────────────────────────────────────────────────────────
Provides three FastAPI Depends()-compatible callables:

  get_current_user          → verify Supabase JWT, return user object (401 if invalid)
  get_current_user_optional → same, but returns None for unauthenticated requests
  require_admin             → verify ADMIN_SECRET Bearer token (403 if wrong)
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.db.supabase import supabase

# ── Bearer extractors ──────────────────────────────────────────────────────────
_bearer = HTTPBearer(auto_error=True)
_bearer_optional = HTTPBearer(auto_error=False)


# ── User auth ──────────────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    """
    Verify a Supabase-issued JWT and return the authenticated user object.

    The frontend sends: Authorization: Bearer <supabase_access_token>
    """
    token = credentials.credentials
    try:
        user_resp = supabase.auth.get_user(token)
        if not user_resp or not user_resp.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_resp.user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_optional),
):
    """Like get_current_user but returns None for unauthenticated requests."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# ── Admin auth ─────────────────────────────────────────────────────────────────

async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    """
    Verify an admin request by comparing the Bearer token against ADMIN_SECRET.
    """
    if not settings.ADMIN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin authentication is not configured on this server.",
        )
    if credentials.credentials != settings.ADMIN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access denied.",
        )
    return True
