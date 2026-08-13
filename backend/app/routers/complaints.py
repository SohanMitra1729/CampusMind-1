"""
app/routers/complaints.py — Complaint Management Routes
────────────────────────────────────────────────────────
Handles:
  POST   /api/complaint/classify
  POST   /api/complaint
  POST   /api/complaint/{complaint_id}/vote
  GET    /api/my-complaints
  GET    /api/admin/complaints
  PATCH  /api/admin/complaints/{complaint_id}/status
  GET    /api/hostels
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends

from app.core.security import get_current_user, get_current_user_optional, require_admin
from app.core.deps import fetch_profile
from app.schemas.complaint import (
    ComplaintClassifyRequest,
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
        raise HTTPException(status_code=500, detail=str(e))


# ── Student: complaints ────────────────────────────────────────────────────────

@router.post("/api/complaint/classify")
async def complaint_classify(
    req: ComplaintClassifyRequest,
    current_user=Depends(get_current_user_optional),
):
    """Fast LLM classification — no DB writes. Used for live frontend feedback."""
    return complaint_service.classify_only(req.text)


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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Complaint submission failed: {str(e)}")


@router.post("/api/complaint/{complaint_id}/vote")
async def vote_complaint(complaint_id: str, current_user=Depends(get_current_user)):
    """Upvote an existing complaint ('I have the same issue'). Returns 409 if already voted."""
    user_id   = str(current_user.id)
    user_info = await fetch_profile(user_id)
    try:
        return complaint_service.vote(complaint_id, user_info)
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vote failed: {str(e)}")


@router.get("/api/my-complaints")
async def get_my_complaints(current_user=Depends(get_current_user)):
    """Return all complaints submitted by the authenticated student."""
    try:
        return complaint_service.get_user_complaints(str(current_user.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Admin: complaints ──────────────────────────────────────────────────────────

@router.get("/api/admin/complaints")
async def list_complaints(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    _admin=Depends(require_admin),
):
    """Admin endpoint: all complaints, filterable by status and category."""
    try:
        return complaint_service.get_all_complaints(status=status, category=category, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
