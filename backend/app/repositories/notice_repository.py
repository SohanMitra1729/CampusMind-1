"""
app/repositories/notice_repository.py — Notices & User Notifications Data Access Layer
──────────────────────────────────────────────────────────────────────────────────
Encapsulates all Supabase database queries for administrative notices and student notifications.
"""

from typing import Any, Dict, List, Optional
from app.db.supabase import supabase


# ── Notices ─────────────────────────────────────────────────────────────────────

def create_notice(data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a new notice into the notices table."""
    res = supabase.table("notices").insert(data).execute()
    return res.data[0] if res.data else data


def get_all_notices(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch recent notices, newest first (admin view)."""
    res = (
        supabase.table("notices")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def get_notice_types_by_ids(notice_ids: List[str]) -> Dict[str, str]:
    """Fetch notice_type for a batch of notice IDs, returning a mapping {notice_id: notice_type}."""
    if not notice_ids:
        return {}
    res = supabase.table("notices").select("id, notice_type").in_("id", notice_ids).execute()
    return {n["id"]: n["notice_type"] for n in (res.data or [])}


# ── User Notifications ──────────────────────────────────────────────────────────

def create_user_notifications_batch(rows: List[Dict[str, Any]], batch_size: int = 50):
    """Insert user_notifications rows in batches to avoid payload limits."""
    if not rows:
        return
    for i in range(0, len(rows), batch_size):
        supabase.table("user_notifications").insert(rows[i : i + batch_size]).execute()


def get_user_notifications(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch notifications for a specific user, newest first."""
    res = (
        supabase.table("user_notifications")
        .select("id, notice_id, notification_title, notification_message, is_read, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def is_notification_owned_by_user(notif_id: str, user_id: str) -> bool:
    """Verify that a user_notification row belongs to the given user."""
    res = (
        supabase.table("user_notifications")
        .select("id")
        .eq("id", notif_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(res.data)


def mark_notification_read(notif_id: str, user_id: str) -> bool:
    """Mark a single notification as read if owned by the user."""
    if not is_notification_owned_by_user(notif_id, user_id):
        return False
    supabase.table("user_notifications").update({"is_read": True}).eq("id", notif_id).execute()
    return True


def mark_all_notifications_read(user_id: str):
    """Mark all unread notifications for a user as read."""
    supabase.table("user_notifications").update({"is_read": True}).eq("user_id", user_id).eq("is_read", False).execute()
