"""
app/routers/auth.py — Authentication & Admin Auth Routes
──────────────────────────────────────────────────────────
Handles:
  POST /api/auth/signup
  POST /api/auth/login
  POST /api/auth/forgot-password
  POST /api/auth/reset-password
  POST /api/admin/auth
"""

from fastapi import APIRouter, HTTPException, Depends

from app.core.config import settings
from app.schemas.auth import (
    SignUpRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    AdminAuthRequest,
)
import app.services.auth_service as auth_service

router = APIRouter()


# ── Admin credential check (not JWT — returns the ADMIN_SECRET token) ─────────

@router.post("/api/admin/auth")
async def admin_auth(req: AdminAuthRequest):
    """Verify admin username/password and return the bearer token."""
    if not settings.ADMIN_USERNAME or not settings.ADMIN_SECRET:
        raise HTTPException(status_code=500, detail="Admin credentials not configured on server.")
    if req.username != settings.ADMIN_USERNAME or req.password != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin credentials.")
    return {"token": settings.ADMIN_SECRET}


# ── Student auth ───────────────────────────────────────────────────────────────

@router.post("/api/auth/signup")
async def signup(req: SignUpRequest):
    try:
        return auth_service.sign_up(
            email=req.email,
            password=req.password,
            name=req.name,
            username=req.username,
            scholar_id=req.scholar_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/auth/login")
async def login(req: LoginRequest):
    try:
        return auth_service.login(req.identifier, req.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Wrong password, unconfirmed email, etc. — auth failure = 401
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/api/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    try:
        return auth_service.forgot_password(req.identifier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/auth/reset-password")
async def reset_password(req: ResetPasswordRequest):
    try:
        return auth_service.reset_password(req.access_token, req.password)
    except ValueError as e:
        # Invalid/expired token — 401 Unauthorized
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
