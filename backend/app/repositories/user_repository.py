"""
app/repositories/user_repository.py — User & Profile Data Access Layer
─────────────────────────────────────────────────────────────────────
Encapsulates all Supabase database queries for student and staff profiles.
"""

from typing import Any, Dict, List, Optional
from app.db.supabase import supabase


def get_profile_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a user's full profile by their Auth user UUID."""
    try:
        res = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        return res.data
    except Exception:
        return None


def get_email_by_username(username: str) -> Optional[str]:
    """Resolve a username to its corresponding registered email address."""
    res = supabase.table("profiles").select("email").eq("username", username).execute()
    if res.data:
        return res.data[0].get("email")
    return None


def get_profile_by_scholar_id(scholar_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a profile by 7-digit scholar ID."""
    res = supabase.table("profiles").select("id, name, scholar_id, telegram_chat_id").eq("scholar_id", scholar_id).execute()
    return res.data[0] if res.data else None


def get_profile_by_telegram_chat_id(chat_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a profile linked to a specific Telegram chat ID."""
    res = supabase.table("profiles").select("*").eq("telegram_chat_id", str(chat_id)).execute()
    return res.data[0] if res.data else None


def link_telegram_chat_id(user_id: str, chat_id: str) -> bool:
    """Link a Telegram chat ID to a user's profile."""
    res = supabase.table("profiles").update({"telegram_chat_id": str(chat_id)}).eq("id", user_id).execute()
    return bool(res.data)


def get_profiles_by_scholar_ids(scholar_ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch profile basic details (id, name, scholar_id) matching a list of scholar IDs."""
    if not scholar_ids:
        return []
    res = (
        supabase.table("profiles")
        .select("id, name, scholar_id")
        .in_("scholar_id", scholar_ids)
        .execute()
    )
    return res.data or []


def get_all_student_profiles() -> List[Dict[str, Any]]:
    """Fetch all student profiles (for broadcast notices)."""
    res = supabase.table("profiles").select("id, name, scholar_id").execute()
    return res.data or []


def get_telegram_enabled_profiles(user_ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch profiles matching user_ids that have a Telegram chat ID linked."""
    if not user_ids:
        return []
    res = (
        supabase.table("profiles")
        .select("id, name, telegram_chat_id")
        .in_("id", user_ids)
        .not_.is_("telegram_chat_id", "null")
        .execute()
    )
    return res.data or []
