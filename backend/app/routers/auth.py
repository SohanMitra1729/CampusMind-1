"""
app/routers/auth.py — Authentication & Admin Auth Routes
──────────────────────────────────────────────────────────
Handles:
  POST /api/admin/auth
  POST /api/auth/signup
  POST /api/auth/login
  POST /api/auth/forgot-password
  POST /api/auth/reset-password
"""

from fastapi import APIRouter

from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import (
    ValidationException,
    UnauthorizedException,
    ForbiddenException,
    InternalServerErrorException,
)
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
        raise InternalServerErrorException("Admin credentials not configured on server.")
    if req.username != settings.ADMIN_USERNAME or req.password != settings.ADMIN_SECRET:
        raise ForbiddenException("Invalid admin credentials.")
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
        raise ValidationException(str(e))
    except Exception as e:
        logger.exception(f"[Auth] Signup failed: {e}")
        raise ValidationException(str(e))


@router.post("/api/auth/login")
async def login(req: LoginRequest):
    try:
        return auth_service.login(req.identifier, req.password)
    except ValueError as e:
        raise ValidationException(str(e))
    except Exception as e:
        # Wrong credentials, unconfirmed email, etc. -> 401 Unauthorized
        logger.warning(f"[Auth] Login failed for {req.identifier}: {e}")
        raise UnauthorizedException("Invalid username, email, or password.")


@router.post("/api/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    try:
        return auth_service.forgot_password(req.identifier)
    except ValueError as e:
        raise ValidationException(str(e))
    except Exception as e:
        logger.exception(f"[Auth] Forgot password request error: {e}")
        raise ValidationException("Could not process password reset request. Please check the identifier.")


@router.post("/api/auth/reset-password")
async def reset_password(req: ResetPasswordRequest):
    try:
        return auth_service.reset_password(req.access_token, req.password)
    except ValueError as e:
        raise UnauthorizedException(str(e))
    except Exception as e:
        logger.exception(f"[Auth] Reset password error: {e}")
        raise ValidationException("Failed to reset password. Please request a new reset link.")
