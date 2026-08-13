"""
app/services/complaint_service.py — Complaint Business Logic
─────────────────────────────────────────────────────────────
Orchestrates complaint operations:
  - classify_only  → fast LLM classification, no DB writes
  - submit         → full pipeline: classify → similar → enrich → save → forward
  - vote           → upvote deduplication + count increment
  - get_user       → student's own complaints with icon enrichment
  - get_all        → admin view with icon enrichment
  - update_status  → admin status change

Why a service?
  The icon/label enrichment for, display is business logic, not HTTP.
  It also calls complaint_agent (LLM) + complaint_repository (DB) together —
  that coordination belongs here, not in the route.
"""

from typing import Any, Dict, List, Optional
import app.repositories.complaint_repository as complaint_repo
from complaint_agent import (
    classify_complaint,
    process_complaint,
    vote_on_complaint,
    CATEGORY_ICONS,
    STATUS_LABELS,
)


# ── Icon enrichment helper ─────────────────────────────────────────────────────

def _enrich_complaint(c: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add display-friendly icon/label fields to a complaint dict.
    Mutates and returns the same dict (list comprehensions stay clean).
    """
    cat  = c.get("category", "general")
    stat = c.get("status", "open")
    c["category_icon"] = CATEGORY_ICONS.get(cat, "📢")
    c["status_icon"]   = STATUS_LABELS.get(stat, ("🔴", "Open"))[0]
    c["status_label"]  = STATUS_LABELS.get(stat, ("🔴", "Open"))[1]
    return c


# ── Fast classify (no DB) ─────────────────────────────────────────────────────

def classify_only(text: str) -> Dict[str, Any]:
    """
    Lightweight LLM call: classify text as complaint or not.
    No DB writes — used by the frontend to show live feedback while typing.

    Returns:
        { is_complaint, category, title, confidence }
    """
    try:
        return classify_complaint(text)
    except Exception:
        # Never crash the frontend on a classify failure — return safe default
        return {"is_complaint": False, "category": "not_complaint", "title": "", "confidence": 0.0}


# ── Full complaint submission ──────────────────────────────────────────────────

def submit_complaint(
    text: str,
    user_info: Dict[str, Any],
    hostel_id: Optional[str] = None,
    room_number: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full 5-stage complaint pipeline via complaint_agent.
    Stages: classify → find similar → enrich hostel → save → forward to staff bot.

    Returns:
        { complaint, similar, hostel_details, category, title }

    Raises:
        ValueError       if text is not actually a complaint (LLM decision)
        Exception        for any DB / LLM errors (re-raised to route)
    """
    if not text or not text.strip():
        raise ValueError("Complaint text is required.")

    result = process_complaint(
        text=text,
        user_info=user_info,
        hostel_id=hostel_id,
        room_number=room_number,
    )

    if result.get("error") == "not_a_complaint":
        raise ValueError(result["message"])

    return result


# ── Vote on complaint ─────────────────────────────────────────────────────────

def vote(complaint_id: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upvote an existing complaint.
    Raises PermissionError (mapped to HTTP 409) if user already voted.
    """
    result = vote_on_complaint(complaint_id, user_info)

    if result.get("error") == "already_voted":
        raise PermissionError(result["message"])

    return result


# ── Student: own complaints ────────────────────────────────────────────────────

def get_user_complaints(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch the authenticated student's complaints with icon enrichment."""
    complaints = complaint_repo.get_user_complaints(user_id, limit=limit)
    return [_enrich_complaint(c) for c in complaints]


# ── Admin: all complaints ─────────────────────────────────────────────────────

def get_all_complaints(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Fetch all complaints (admin view) with optional filters + icon enrichment."""
    complaints = complaint_repo.get_all_complaints(status=status, category=category, limit=limit)
    return [_enrich_complaint(c) for c in complaints]


# ── Admin: update status ───────────────────────────────────────────────────────

VALID_STATUSES = {"open", "in_progress", "resolved", "dismissed"}

def update_complaint_status(complaint_id: str, new_status: str) -> Dict[str, Any]:
    """
    Admin action: change a complaint's status.

    Raises:
        ValueError       for unknown status string
        LookupError      if complaint_id doesn't exist
    """
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(VALID_STATUSES)}")

    updated = complaint_repo.update_complaint_status(complaint_id, new_status)
    if not updated:
        raise LookupError("Complaint not found.")

    return {"message": f"Status updated to '{new_status}'.", "complaint": updated}


# ── Public: hostel list ────────────────────────────────────────────────────────

def get_hostels() -> List[Dict[str, Any]]:
    """Return all hostels for the complaint submission dropdown."""
    return complaint_repo.get_all_hostels()
