"""
app/services/chat_service.py — Chat & RAG Business Logic
──────────────────────────────────────────────────────────
Orchestrates the full chat pipeline:
  1. Create or validate the chat session
  2. Persist the user message
  3. Fetch recent history for RAG context
  3b. [COMPLAINT SHORTCUT] If an active complaint session exists → route to
      the conversational dialogue agent (skip RAG entirely).
  3c. [COMPLAINT DETECT] Classify the message first; if it is a complaint
      with confidence >= 0.60, start a new dialogue session and return the
      intake prompt (skip RAG entirely — no mixed messages).
  4. Run the RAG pipeline (only when message is NOT a complaint)
  5. Persist the bot reply

Why a service?
  The route (main.py) only needs to know:
    - Was ownership denied?  → raise 403
    - What's the result?     → return it
  Everything else lives here.
"""

from typing import Any, Dict, Optional
import app.repositories.chat_repository as chat_repo
from app.services.rag_service import get_answer
from app.services.complaint_agent import classify_complaint
from app.services.complaint_dialogue_agent import (
    has_active_complaint_session,
    handle_complaint_turn,
    start_complaint_session,
)

# Minimum classification confidence to trigger conversational complaint intake
_COMPLAINT_CONFIDENCE_THRESHOLD = 0.60


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_title(query: str) -> str:
    """Auto-generate a chat title from the first user message (max 50 chars)."""
    return query[:50] + "..." if len(query) > 50 else query


# ── Core pipeline ──────────────────────────────────────────────────────────────

async def handle_chat(
    user_id: str,
    user_info: Dict[str, Any],
    query: str,
    chat_id: Optional[str],
    metadata_filter: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Full chat pipeline for a single user turn.

    Args:
        user_id:         Verified UUID from JWT (never trust client-sent IDs!).
        user_info:       Full profile row from user_repository (name, scholar_id…).
        query:           The student's current message.
        chat_id:         Existing chat session UUID, or None to start a new chat.
        metadata_filter: Optional Supabase filter for RAG document scoping.

    Returns:
        {
            "answer":   str,
            "sources":  list,
            "chat_id":  str,
            "title":    str,
        }

    Raises:
        PermissionError  if chat_id is supplied but doesn't belong to user_id.
    """
    # ── Step 1: Resolve or create the chat session ─────────────────────────────
    if not chat_id:
        # Brand new conversation — create and get the generated UUID back
        title    = _build_title(query)
        new_chat = chat_repo.create_chat(user_id, title)
        chat_id  = new_chat["id"]
    else:
        # Existing chat — verify it belongs to this user (prevents IDOR)
        existing = chat_repo.get_chat_by_id_and_user(chat_id, user_id)
        if not existing:
            raise PermissionError("Chat not found or access denied.")
        title = existing["title"]

    # ── Step 2: Persist user message ───────────────────────────────────────────
    chat_repo.add_message(chat_id, "user", query)

    # ── Step 3: Fetch recent history for RAG context window ───────────────────
    # Last 6 messages = ~3 user/bot turns; keeps the prompt short but contextual
    chat_history = chat_repo.get_recent_history(chat_id, limit=6)

    # ── Step 3b: Complaint dialogue shortcut ──────────────────────────────────
    # If a multi-turn complaint session is already in progress for this chat,
    # route directly to the dialogue agent — skip RAG entirely.
    if has_active_complaint_session(chat_id):
        dialogue_reply = handle_complaint_turn(
            chat_id=chat_id,
            user_message=query,
            user_info=user_info,
        )
        if dialogue_reply is not None:
            chat_repo.add_message(chat_id, "bot", dialogue_reply)
            return {
                "answer":  dialogue_reply,
                "sources": [],
                "chat_id": chat_id,
                "title":   title,
            }
        # dialogue_reply is None → session was cleared, fall through to RAG

    # ── Step 3c: Detect new complaint intent BEFORE running RAG ───────────────
    # Classify first so the user gets a clean, focused complaint intake prompt
    # instead of a contradictory mix of "contact staff" + "file a complaint".
    try:
        active_tickets = complaint_repo.get_user_active_open_tickets(user_id) if user_id else []
        clf = classify_complaint(query, active_tickets=active_tickets)
        if (
            clf.get("is_complaint")
            and float(clf.get("confidence", 0)) >= _COMPLAINT_CONFIDENCE_THRESHOLD
            and clf.get("category") != "not_complaint"
        ):
            intake_prompt = start_complaint_session(
                chat_id=chat_id,
                complaint_text=query,
                classification=clf,
                user_info=user_info,
            )
            chat_repo.add_message(chat_id, "bot", intake_prompt)
            return {
                "answer":  intake_prompt,
                "sources": [],
                "chat_id": chat_id,
                "title":   title,
            }
    except Exception as clf_err:
        # Classify is non-critical — never let it block the chat response
        import logging
        logging.getLogger(__name__).warning(
            f"[ChatService] classify error (non-fatal): {clf_err}"
        )

    # ── Step 4: Run the RAG pipeline ──────────────────────────────────────────
    # Only reached when the message is clearly NOT a complaint.
    result = await get_answer(
        query,
        metadata_filter=metadata_filter,
        user_info=user_info,
        chat_history=chat_history,
    )

    # ── Step 5: Persist bot reply ─────────────────────────────────────────────
    chat_repo.add_message(chat_id, "bot", result["answer"])

    # Attach session identifiers to the result so the frontend can track them
    result["chat_id"] = chat_id
    result["title"]   = title

    return result


# ── Chat list & messages ───────────────────────────────────────────────────────

def get_user_chats(user_id: str):
    """Return all chat sessions for a user (newest first)."""
    return chat_repo.get_user_chats(user_id)


def delete_chat(chat_id: str, user_id: str) -> bool:
    """
    Delete a chat session.
    Returns False if chat not found or doesn't belong to user_id.
    """
    return chat_repo.delete_chat(chat_id, user_id)


def get_chat_messages(chat_id: str, user_id: str):
    """
    Fetch all messages for a chat session.
    Raises PermissionError if chat doesn't belong to user_id.
    """
    chat = chat_repo.get_chat_by_id_and_user(chat_id, user_id)
    if not chat:
        raise PermissionError("Chat not found or access denied.")
    return chat_repo.get_chat_messages(chat_id)

