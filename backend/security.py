"""
security.py — Authentication & Authorization dependencies for FastAPI
────────────────────────────────────────────────────────────────────
Provides three FastAPI Depends()-compatible callables:

  get_current_user          → verify Supabase JWT, return user object (401 if invalid)
  get_current_user_optional → same, but returns None for unauthenticated requests
  require_admin             → verify ADMIN_SECRET Bearer token (403 if wrong)

Usage:
    from security import get_current_user, get_current_user_optional, require_admin

    @app.get("/api/chats")
    async def get_chats(current_user = Depends(get_current_user)):
        user_id = str(current_user.id)
        ...

    @app.get("/api/admin/documents")
    async def list_documents(_admin = Depends(require_admin)):
        ...
"""

import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ── Bearer extractors ──────────────────────────────────────────────────────────
# auto_error=True  → returns 403 automatically when Authorization header is missing
# auto_error=False → allows optional authentication (returns None credentials)
_bearer          = HTTPBearer(auto_error=True)
_bearer_optional = HTTPBearer(auto_error=False)


def _get_supabase():
    """
    Lazy import of the Supabase client to avoid a circular import at module load.
    (rag.py creates the client; security.py is loaded by main.py before rag.py
    finishes its top-level setup in some edge cases.)
    This will be cleaned up in Phase 2 when we have a proper db/ singleton.
    """
    from rag import supabase
    return supabase


# ── User auth ──────────────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    """
    Verify a Supabase-issued JWT and return the authenticated user object.

    The frontend sends:  Authorization: Bearer <supabase_access_token>

    Raises:
        HTTP 401 — token missing, invalid, or expired
    """
    token = credentials.credentials
    try:
        sb = _get_supabase()
        user_resp = sb.auth.get_user(token)
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
    """
    Like get_current_user but returns None for unauthenticated requests.
    Use on endpoints that work for both logged-in and anonymous users.
    """
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

    Flow:
      1. Admin calls POST /api/admin/auth with {username, password}
      2. Backend verifies against ADMIN_USERNAME + ADMIN_SECRET env vars
      3. Returns {"token": ADMIN_SECRET}
      4. Frontend stores token, sends it as Bearer on all /api/admin/* calls
      5. This dependency verifies it on every protected endpoint

    Raises:
        HTTP 500 — ADMIN_SECRET not configured in environment
        HTTP 403 — token does not match ADMIN_SECRET
    """
    admin_secret = os.environ.get("ADMIN_SECRET", "")
    if not admin_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin authentication is not configured on this server.",
        )
    if credentials.credentials != admin_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access denied.",
        )
    return True
