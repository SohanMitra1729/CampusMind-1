"""
app/repositories/chat_repository.py — Chat Data Access Layer
────────────────────────────────────────────────────────────
Encapsulates all Supabase database queries for chat sessions and messages.
"""

from typing import Any, Dict, List, Optional
from app.db.supabase import supabase


def create_chat(user_id: str, title: str) -> Dict[str, Any]:
    """Create a new chat session for a user and return the inserted row."""
    res = supabase.table("chats").insert({"user_id": user_id, "title": title}).execute()
    return res.data[0] if res.data else {}


def get_chat_by_id_and_user(chat_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a chat session by ID, verifying that it belongs to the given user."""
    res = (
        supabase.table("chats")
        .select("id, title, created_at")
        .eq("id", chat_id)
        .eq("user_id", user_id)
        .execute()
    )
    return res.data[0] if res.data else None


def get_user_chats(user_id: str) -> List[Dict[str, Any]]:
    """Fetch all chat sessions for a specific user, newest first."""
    res = (
        supabase.table("chats")
        .select("id, title, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def delete_chat(chat_id: str, user_id: str) -> bool:
    """Delete a chat session and all its associated messages."""
    chat = get_chat_by_id_and_user(chat_id, user_id)
    if not chat:
        return False
    try:
        # Cascade delete child messages first
        supabase.table("messages").delete().eq("chat_id", chat_id).execute()
    except Exception as e:
        print(f"[ChatRepo] delete messages error for chat {chat_id}: {e}")

    res = supabase.table("chats").delete().eq("id", chat_id).execute()
    return bool(res.data)


def add_message(chat_id: str, role: str, content: str) -> Dict[str, Any]:
    """Insert a new user or bot message into a chat session."""
    res = (
        supabase.table("messages")
        .insert({"chat_id": chat_id, "role": role, "content": content})
        .execute()
    )
    return res.data[0] if res.data else {}


def get_chat_messages(chat_id: str) -> List[Dict[str, Any]]:
    """Fetch all messages in a chat session in chronological order."""
    res = (
        supabase.table("messages")
        .select("id, role, content, created_at")
        .eq("chat_id", chat_id)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []


def get_recent_history(chat_id: str, limit: int = 6) -> List[Dict[str, str]]:
    """
    Fetch the most recent messages for RAG context (excluding the very last message just inserted),
    returned in chronological order.
    """
    msg_res = (
        supabase.table("messages")
        .select("role, content")
        .eq("chat_id", chat_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    # Filter out the very latest message (just added by user) and reverse to chronological order
    history_messages = msg_res.data[1:] if msg_res.data else []
    return history_messages[::-1]
