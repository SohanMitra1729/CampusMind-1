"""
app/routers/complaints.py — Complaint Management Routes
────────────────────────────────────────────────────────
Handles:
  GET    /api/hostels
  POST   /api/complaint
  POST   /api/complaint/{complaint_id}/vote
  GET    /api/my-complaints
  GET    /api/admin/complaints
  PATCH  /api/admin/complaints/{complaint_id}/status
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends

from app.core.security import get_current_user, require_admin
from app.core.deps import fetch_profile
from app.core.logger import logger
from app.core.exceptions import (
    ValidationException,
    NotFoundException,
    ConflictException,
    InternalServerErrorException,
)
from app.schemas.complaint import (
    ComplaintRequest,
    ComplaintStatusRequest,
)
import app.services.complaint_service as complaint_service

router = APIRouter()


# ── Public: hostel list (no auth) ─────────────────────────────────────────────

@router.get("/api/hostels")
async def list_hostels():
    """Return all hostels for the frontend complaint submission dropdown."""
    try:
        return complaint_service.get_hostels()
    except Exception as e:
        logger.exception(f"[Complaints] list_hostels error: {e}")
        raise InternalServerErrorException("Failed to fetch hostels list.")


# ── Student: complaints ────────────────────────────────────────────────────────

@router.post("/api/complaint")
async def submit_complaint(req: ComplaintRequest, current_user=Depends(get_current_user)):
    """Full complaint pipeline: classify → similar → hostel enrich → save → forward."""
    user_id   = str(current_user.id)
    user_info = await fetch_profile(user_id)
    try:
        return complaint_service.submit_complaint(
            text=req.text,
            user_info=user_info,
            hostel_id=req.hostel_id,
            room_number=req.room_number,
        )
    except ValueError as e:
        raise ValidationException(str(e))
    except Exception as e:
        logger.exception(f"[Complaints] Complaint submission failed: {e}")
        raise InternalServerErrorException("Complaint submission failed. Please try again.")


@router.post("/api/complaint/{complaint_id}/vote")
async def vote_complaint(complaint_id: str, current_user=Depends(get_current_user)):
    """Upvote an existing complaint ('I have the same issue'). Returns 409 if already voted."""
    user_id   = str(current_user.id)
    user_info = await fetch_profile(user_id)
    try:
        return complaint_service.vote(complaint_id, user_info)
    except PermissionError as e:
        raise ConflictException(str(e))
    except Exception as e:
        logger.exception(f"[Complaints] Vote failed for complaint {complaint_id}: {e}")
        raise InternalServerErrorException("Failed to register vote.")


@router.get("/api/my-complaints")
async def get_my_complaints(current_user=Depends(get_current_user)):
    """Return all complaints submitted by the authenticated student."""
    try:
        return complaint_service.get_user_complaints(str(current_user.id))
    except Exception as e:
        logger.exception(f"[Complaints] get_my_complaints error: {e}")
        raise InternalServerErrorException("Failed to fetch complaints history.")


# ── Admin: complaints ──────────────────────────────────────────────────────────

@router.get("/api/admin/complaints")
async def list_complaints(
    status: Optional[str] = None,
    category: Optional[str] = None,
    staff_role: Optional[str] = None,
    scope: Optional[str] = None,
    limit: int = 50,
    _admin=Depends(require_admin),
):
    """Admin endpoint: all complaints, filterable by status, category, staff_role, and scope."""
    try:
        return complaint_service.get_all_complaints(
            status=status,
            category=category,
            staff_role=staff_role,
            scope=scope,
            limit=limit,
        )
    except Exception as e:
        logger.exception(f"[Complaints] list_complaints admin error: {e}")
        raise InternalServerErrorException("Failed to load complaints.")


@router.patch("/api/admin/complaints/{complaint_id}/status")
async def update_complaint_status(
    complaint_id: str,
    req: ComplaintStatusRequest,
    _admin=Depends(require_admin),
):
    """Admin action: update a complaint's status."""
    try:
        return complaint_service.update_complaint_status(complaint_id, req.status)
    except ValueError as e:
        raise ValidationException(str(e))
    except LookupError as e:
        raise NotFoundException(str(e))
    except Exception as e:
        logger.exception(f"[Complaints] update_complaint_status error: {e}")
        raise InternalServerErrorException("Failed to update complaint status.")


@router.delete("/api/admin/complaints/{complaint_id}")
async def delete_complaint(
    complaint_id: str,
    _admin=Depends(require_admin),
):
    """Admin action: permanently delete a complaint."""
    try:
        return complaint_service.delete_complaint(complaint_id)
    except Exception as e:
        logger.exception(f"[Complaints] delete_complaint error for {complaint_id}: {e}")
        raise InternalServerErrorException("Failed to delete complaint.")
