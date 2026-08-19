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


def get_notice_types_by_ids(notice_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Fetch notice metadata (type, source_file, content, title) for a batch of notice IDs."""
    if not notice_ids:
        return {}
    res = supabase.table("notices").select("id, notice_type, source_type, source_file, title, content, is_broadcast, created_at").in_("id", notice_ids).execute()
    return {n["id"]: n for n in (res.data or [])}


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


def delete_notice_by_id(notice_id: str) -> bool:
    """Delete a notice, its dispatched user notifications, its physical PDF (if any), and its pgvector chunks."""
    try:
        # Fetch notice details first to know source_file and source_type
        res = supabase.table("notices").select("*").eq("id", notice_id).execute()
        notice = res.data[0] if (res.data and len(res.data) > 0) else None

        source_file = notice.get("source_file") if notice else None
        source_type = notice.get("source_type") if notice else "text"
        title = notice.get("title") if notice else None

        # 1. Delete user_notifications for this notice
        supabase.table("user_notifications").delete().eq("notice_id", notice_id).execute()

        # 2. Delete pgvector chunks for this notice by notice_id / source_id
        for field in ["notice_id", "source_id"]:
            try:
                supabase.table("documents").delete().eq(f"metadata->>{field}", notice_id).execute()
            except Exception:
                pass

        # 3. If it was a PDF notice, delete all chunks, cloud storage file, and local cache
        if source_file:
            from pathlib import Path
            clean_file = source_file.strip()
            # Clean chunks in documents
            for field in ["filename", "source", "file_name", "title", "source_file"]:
                try:
                    supabase.table("documents").delete().eq(f"metadata->>{field}", clean_file).execute()
                except Exception:
                    pass
            # Remove from Supabase Storage
            try:
                supabase.storage.from_("campus-documents").remove([clean_file])
            except Exception:
                pass
            # Remove from local disk
            for base_path in [
                Path(__file__).resolve().parent.parent.parent.parent / "data" / "pdfs",
                Path.cwd() / "data" / "pdfs",
                Path.cwd().parent / "data" / "pdfs",
            ]:
                file_path = base_path / clean_file
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except Exception:
                        pass

        # 4. If it was a text notice, also clean up by title
        elif title and source_type == "text":
            try:
                supabase.table("documents").delete().eq("metadata->>source", title).execute()
            except Exception:
                pass

        # 5. Delete notice row
        supabase.table("notices").delete().eq("id", notice_id).execute()
        return True
    except Exception as e:
        print(f"[NoticeRepo] delete_notice_by_id error for {notice_id}: {e}")
        return False
