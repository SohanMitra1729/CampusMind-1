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
"""

from typing import Any, Dict, List, Optional
import app.repositories.complaint_repository as complaint_repo
from app.services.complaint_agent import (
    classify_complaint,
    process_complaint,
    vote_on_complaint,
    CATEGORY_ICONS,
    STATUS_LABELS,
)

# ── Staff role display helpers ─────────────────────────────────────────────────

STAFF_ROLE_LABELS: Dict[str, str] = {
    "electrical":   "Electrical / Maintenance",
    "cleaning":     "Cleaning Staff",
    "maintenance":  "Maintenance (Furniture / Plumbing / Civil)",
    "mess_manager": "Mess Manager",
    "watchmen":     "Watchmen / Security",
}

STAFF_ROLE_ICONS: Dict[str, str] = {
    "electrical":   "⚡",
    "cleaning":     "🧹",
    "maintenance":  "🛠️",
    "mess_manager": "🍽️",
    "watchmen":     "🔒",
}

SCOPE_LABELS: Dict[str, str] = {
    "MESS":            "Mess / Dining",
    "ROOM_SHARED":     "Room (Shared Fixture)",
    "ROOM_INDIVIDUAL": "Personal Inventory",
    "COMMON_AREA":     "Common / Floor Area",
}

SCOPE_ICONS: Dict[str, str] = {
    "MESS":            "🍽️",
    "ROOM_SHARED":     "👥",
    "ROOM_INDIVIDUAL": "👤",
    "COMMON_AREA":     "🏢",
}


# ── Icon enrichment helper ─────────────────────────────────────────────────────

def _enrich_complaint(c: Dict[str, Any]) -> Dict[str, Any]:
    """Add display-friendly icon/label fields to a complaint dict."""
    cat   = c.get("category", "general")
    stat  = c.get("status", "open")
    role  = c.get("staff_role")
    scope = c.get("scope", "COMMON_AREA")
    
    c["category_icon"]    = CATEGORY_ICONS.get(cat, "📢")
    c["status_icon"]      = STATUS_LABELS.get(stat, ("🔴", "Open"))[0]
    c["status_label"]     = STATUS_LABELS.get(stat, ("🔴", "Open"))[1]
    c["staff_role_label"] = STAFF_ROLE_LABELS.get(role, "Unassigned") if role else "Unassigned"
    c["staff_role_icon"]  = STAFF_ROLE_ICONS.get(role, "🏛️") if role else "🏛️"
    c["scope_label"]      = SCOPE_LABELS.get(scope, "Common Area")
    c["scope_icon"]       = SCOPE_ICONS.get(scope, "🏢")
    return c


# ── Fast classify (no DB) ─────────────────────────────────────────────────────

def classify_only(text: str) -> Dict[str, Any]:
    """Lightweight LLM call: classify text as complaint or not."""
    try:
        return classify_complaint(text)
    except Exception:
        return {"is_complaint": False, "category": "not_complaint", "title": "", "confidence": 0.0, "scope": "COMMON_AREA"}


# ── Full complaint submission ──────────────────────────────────────────────────

def submit_complaint(
    text: str,
    user_info: Dict[str, Any],
    hostel_id: Optional[str] = None,
    room_number: Optional[str] = None,
) -> Dict[str, Any]:
    """Full complaint pipeline via complaint_agent."""
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
    if result.get("error") == "already_open":
        raise ValueError(result["message"])

    return result


# ── Vote on complaint ─────────────────────────────────────────────────────────

def vote(complaint_id: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
    """Upvote an existing complaint."""
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
    staff_role: Optional[str] = None,
    scope: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Fetch all complaints (admin view) with optional filters + icon enrichment."""
    complaints = complaint_repo.get_all_complaints(
        status=status,
        category=category,
        staff_role=staff_role,
        scope=scope,
        limit=limit,
    )
    return [_enrich_complaint(c) for c in complaints]


# ── Admin: update status ───────────────────────────────────────────────────────

VALID_STATUSES = {"open", "in_progress", "resolved", "dismissed"}

def update_complaint_status(complaint_id: str, new_status: str) -> Dict[str, Any]:
    """Admin action: change a complaint's status."""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(VALID_STATUSES)}")

    updated = complaint_repo.update_complaint_status(complaint_id, new_status)
    if not updated:
        raise LookupError("Complaint not found.")

    return {"message": f"Status updated to '{new_status}'.", "complaint": updated}


def delete_complaint(complaint_id: str) -> Dict[str, Any]:
    """Admin action: permanently delete a complaint."""
    deleted = complaint_repo.delete_complaint_by_id(complaint_id)
    return {"message": f"Complaint {complaint_id} deleted successfully.", "deleted": deleted}


# ── Public: hostel list ────────────────────────────────────────────────────────

def get_hostels() -> List[Dict[str, Any]]:
    """Return all hostels for the complaint submission dropdown."""
    return complaint_repo.get_all_hostels()
