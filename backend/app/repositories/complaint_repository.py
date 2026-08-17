"""
app/repositories/complaint_repository.py — Complaints & Hostels Data Access Layer
─────────────────────────────────────────────────────────────────────────────────
Encapsulates all Supabase database queries for complaints, votes, and hostels.
"""

from typing import Any, Dict, List, Optional
from app.db.supabase import supabase


# ── Hostels ─────────────────────────────────────────────────────────────────────

def get_all_hostels() -> List[Dict[str, Any]]:
    """Fetch all hostels for frontend dropdowns and dialogue matching."""
    res = supabase.table("hostels").select("id, name, code, gender, target_years, sharing_types, sharing_description, mess_id, mess_name, aliases").order("name").execute()
    return res.data or []


def get_hostel_by_id(hostel_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single hostel by UUID with topology details."""
    if not hostel_id:
        return None
    try:
        res = (
            supabase.table("hostels")
            .select("id, name, code, gender, target_years, sharing_types, sharing_description, mess_id, mess_name, aliases")
            .eq("id", hostel_id)
            .single()
            .execute()
        )
        return res.data
    except Exception:
        return None


# ── Complaints ──────────────────────────────────────────────────────────────────

def create_complaint(data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a new complaint row into Supabase."""
    res = supabase.table("complaints").insert(data).execute()
    return res.data[0] if res.data else data


def get_complaint_by_id(complaint_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a complaint by UUID."""
    try:
        res = supabase.table("complaints").select("*").eq("id", complaint_id).single().execute()
        return res.data
    except Exception:
        return None


def get_user_complaints(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch all complaints submitted by a specific student, newest first."""
    res = (
        supabase.table("complaints")
        .select("id, title, description, category, status, staff_role, scope, mess_id, vote_count, hostel_details, created_at, updated_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def get_all_complaints(
    status: Optional[str] = None,
    category: Optional[str] = None,
    staff_role: Optional[str] = None,
    scope: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Admin query: fetch complaints with optional filtering by status, category, staff_role, scope."""
    query = (
        supabase.table("complaints")
        .select("id, user_id, scholar_id, student_name, title, description, "
                "category, status, staff_role, scope, mess_id, hostel_details, hostel_id, room_number, vote_count, created_at, updated_at")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if category:
        query = query.eq("category", category)
    if staff_role:
        query = query.eq("staff_role", staff_role)
    if scope:
        query = query.eq("scope", scope)

    res = query.execute()
    return res.data or []


def update_complaint_status(complaint_id: str, status: str) -> Optional[Dict[str, Any]]:
    """Update a complaint's status string."""
    res = (
        supabase.table("complaints")
        .update({"status": status, "updated_at": "now()"})
        .eq("id", complaint_id)
        .execute()
    )
    return res.data[0] if res.data else None


def get_open_complaints_by_scope(
    scope: str,
    mess_id: Optional[str] = None,
    hostel_id: Optional[str] = None,
    room_number: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Query open complaints filtered by specific scope context for high-precision deduplication."""
    query = supabase.table("complaints").select("id, title, description, category, staff_role, scope, mess_id, hostel_id, room_number, vote_count, status").in_("status", ["open", "in_progress"])
    
    if scope == "MESS" and mess_id:
        query = query.eq("scope", "MESS").eq("mess_id", mess_id)
    elif scope == "ROOM_SHARED" and hostel_id and room_number:
        query = query.eq("scope", "ROOM_SHARED").eq("hostel_id", hostel_id).eq("room_number", room_number)
    else:
        if hostel_id:
            query = query.eq("hostel_id", hostel_id)
        query = query.eq("scope", scope)

    res = query.order("vote_count", desc=True).limit(limit).execute()
    return res.data or []


def get_user_active_open_tickets(user_id: str, limit: int = 6) -> List[Dict[str, Any]]:
    """Retrieve student's active open and in_progress tickets for semantic duplicate detection."""
    if not user_id:
        return []
    try:
        res = (
            supabase.table("complaints")
            .select("id, title, description, category, staff_role, scope, status, created_at")
            .eq("user_id", user_id)
            .in_("status", ["open", "in_progress"])
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def get_open_complaints_for_similarity(limit: int = 30) -> List[Dict[str, Any]]:
    """Fetch open complaints sorted by vote count for similarity matching."""
    res = (
        supabase.table("complaints")
        .select("id, title, vote_count, description, category, staff_role, scope, mess_id, status")
        .eq("status", "open")
        .order("vote_count", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


# ── Complaint Votes ─────────────────────────────────────────────────────────────

def has_user_voted(complaint_id: str, user_id: str) -> bool:
    """Check if a user has already voted on a specific complaint."""
    res = (
        supabase.table("complaint_votes")
        .select("id")
        .eq("complaint_id", complaint_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(res.data)


def record_vote(complaint_id: str, user_id: str, scholar_id: Optional[str] = None) -> bool:
    """Record a vote entry in complaint_votes."""
    try:
        supabase.table("complaint_votes").insert({
            "complaint_id": complaint_id,
            "user_id": user_id,
            "scholar_id": scholar_id or None,
        }).execute()
        return True
    except Exception:
        return False


def increment_vote_count(complaint_id: str) -> int:
    """Atomically increment vote_count via PostgreSQL RPC stored procedure with fallback."""
    try:
        res = supabase.rpc("increment_complaint_vote", {"target_complaint_id": complaint_id}).execute()
        if res.data is not None:
            return int(res.data)
    except Exception:
        pass

    # Fallback to read-and-update if RPC is not present
    current = (
        supabase.table("complaints")
        .select("vote_count")
        .eq("id", complaint_id)
        .execute()
    )
    current_count = current.data[0]["vote_count"] if current.data else 0
    new_count = current_count + 1

    supabase.table("complaints").update({"vote_count": new_count}).eq("id", complaint_id).execute()
    return new_count
