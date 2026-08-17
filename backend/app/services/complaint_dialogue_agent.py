"""
app/services/complaint_dialogue_agent.py — Conversational Complaint Filing Agent
────────────────────────────────────────────────────────────────────────────────
Manages multi-turn complaint intake entirely inside the chat interface.

Session states stored in bot_sessions (keyed by chat_id):
  complaint_awaiting_hostel  → asked user for hostel name
  complaint_awaiting_room    → asked user for room number

Turn flow:
  User reports problem
    ↓  classify_complaint() detects complaint with confidence >= 0.6
  Bot asks: "Which hostel are you staying in?"
    ↓  user replies with hostel name → fuzzy matched against DB
  Bot asks: "What is your room number?" (only if needs_room=True)
    ↓  user replies with room number
  Bot submits complaint → returns formatted confirmation in chat
"""

import re
from typing import Optional, Dict, Any, List

from app.core.logger import logger
from app.db.supabase import supabase
import app.repositories.complaint_repository as complaint_repo
from app.services.complaint_agent import classify_complaint, process_complaint

# ── Session state constants ────────────────────────────────────────────────────

STATE_AWAITING_HOSTEL = "complaint_awaiting_hostel"
STATE_AWAITING_ROOM   = "complaint_awaiting_room"

CANCEL_KEYWORDS = {
    "cancel", "nevermind", "never mind", "stop", "quit", "abort",
    "no complaint", "forget it", "skip", "nope", "exit", "leave it",
}


# ── Session helpers ────────────────────────────────────────────────────────────

def _get_session(chat_id: str) -> Optional[Dict[str, Any]]:
    """Fetch the active complaint session for this chat_id from bot_sessions."""
    try:
        res = (
            supabase.table("bot_sessions")
            .select("state, data")
            .eq("chat_id", chat_id)
            .execute()
        )
        if res.data:
            row = res.data[0]
            state = row.get("state", "")
            if state.startswith("complaint_"):
                return {"state": state, "data": row.get("data") or {}}
    except Exception as e:
        logger.error(f"[ComplaintDialogue] get_session error: {e}")
    return None


def _set_session(chat_id: str, state: str, data: Dict[str, Any]):
    """Upsert the complaint session for this chat_id in bot_sessions."""
    try:
        supabase.table("bot_sessions").upsert({
            "chat_id":    chat_id,
            "state":      state,
            "data":       data,
            "updated_at": "now()",
        }).execute()
    except Exception as e:
        logger.error(f"[ComplaintDialogue] set_session error: {e}")


def _clear_session(chat_id: str):
    """Remove the complaint session for this chat_id from bot_sessions."""
    try:
        supabase.table("bot_sessions").delete().eq("chat_id", chat_id).execute()
    except Exception as e:
        logger.error(f"[ComplaintDialogue] clear_session error: {e}")


# ── Hostel fuzzy matching ──────────────────────────────────────────────────────

def _fuzzy_match_hostel(user_input: str, hostels: List[Dict]) -> Optional[Dict]:
    """
    Match user input against hostel names/codes.
    Priority order:
      1. Exact match against name or code
      2. Number match — if user said a number ("4", "3"), match hostel with that number
      3. All significant tokens match (not just 'hostel' which every name contains)
      4. Best token overlap (excluding the generic word 'hostel')
    """
    text = user_input.lower().strip()
    tokens = set(re.findall(r"\w+", text))
    # Extract any numbers from user input — they are the most specific identifier
    numbers_in_input = set(re.findall(r"\d+", text))
    # Tokens to ignore for scoring since they appear in ALL hostel names
    noise = {"hostel", "the", "my", "i", "am", "in", "at", "it", "is", "a", "no"}
    meaningful_tokens = tokens - noise

    best_score = -1
    best_hostel = None

    for h in hostels:
        name = (h.get("name") or "").lower()
        code = (h.get("code") or "").lower()
        name_tokens = set(re.findall(r"\w+", name)) - noise
        numbers_in_name = set(re.findall(r"\d+", name))

        # 1. Direct full-string match
        if text == name or text == code:
            return h

        # 2. Substring — but only exact word match, not partial
        if code and re.search(rf"\b{re.escape(code)}\b", text):
            return h

        # 3. If user mentioned a number AND hostel name has the same number — strong match
        number_match = bool(numbers_in_input & numbers_in_name)

        # 4. Meaningful token overlap (excludes generic words like 'hostel')
        if meaningful_tokens and name_tokens:
            overlap = len(meaningful_tokens & name_tokens)
        else:
            overlap = 0

        # Score: number match is +10, each overlapping token is +1
        score = (10 if number_match else 0) + overlap

        if score > best_score:
            best_score = score
            best_hostel = h

    # Require at least a number match OR a meaningful word overlap
    return best_hostel if best_score > 0 else None


# ── Public API — called from chat_service ─────────────────────────────────────

def has_active_complaint_session(chat_id: str) -> bool:
    """Return True if there is an in-progress complaint session for this chat_id."""
    return _get_session(chat_id) is not None


def start_complaint_session(
    chat_id: str,
    complaint_text: str,
    classification: Dict[str, Any],
    user_info: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Called when the chat layer detects a complaint intent.
    1. Tries to auto-enrich hostel/room from DB allotment data (scholar_id lookup).
    2. If auto-enriched, skips questions and goes straight to submission.
    3. Otherwise saves session state and asks the first question.
    """
    category   = classification.get("category", "general")
    needs_room = bool(classification.get("needs_room", False))
    staff_role = classification.get("staff_role")
    title      = classification.get("title") or complaint_text[:60]

    # ── Try auto-enrich from hostel allotment data ─────────────────────────────
    if user_info:
        scholar_id = user_info.get("scholar_id") or ""
        if scholar_id:
            try:
                from app.repositories.document_repository import find_hostel_allotment_chunk
                chunk = find_hostel_allotment_chunk(scholar_id)
                if chunk:
                    chunk_text = chunk.get("content", "")
                    # Parse allotment details from pipe-separated format
                    details: Dict[str, str] = {}
                    for pair in chunk_text.split("|"):
                        pair = pair.strip()
                        if ":" in pair:
                            k, v = pair.split(":", 1)
                            details[k.strip().lower().replace(" ", "_")] = v.strip()

                    auto_hostel_name = (
                        details.get("hostel_name")
                        or details.get("hostel")
                        or details.get("allocated_hostel")
                    )
                    auto_room = (
                        details.get("room_no")
                        or details.get("room_number")
                        or details.get("room")
                    )

                    if auto_hostel_name:
                        # Try to resolve hostel_id from the name
                        hostels = complaint_repo.get_all_hostels()
                        matched = _fuzzy_match_hostel(auto_hostel_name, hostels)
                        hostel_id = matched["id"] if matched else None

                        logger.info(
                            f"[ComplaintDialogue] Auto-enriched: hostel={auto_hostel_name} "
                            f"room={auto_room} for scholar_id={scholar_id}"
                        )

                        # Have enough info — submit immediately without asking questions
                        data = {
                            "complaint_text": complaint_text,
                            "category":       category,
                            "title":          title,
                            "needs_room":     needs_room,
                            "staff_role":     staff_role,
                            "hostel_id":      hostel_id,
                            "hostel_name":    auto_hostel_name,
                            "room_number":    auto_room if needs_room else None,
                        }
                        # Need a chat_id-keyed session briefly to call _submit_and_respond
                        _set_session(chat_id, "complaint_auto_submitting", data)
                        result = _submit_and_respond(chat_id, data, user_info)
                        return result

            except Exception as enrich_err:
                logger.warning(f"[ComplaintDialogue] Auto-enrich failed (non-fatal): {enrich_err}")

    # ── Manual intake: ask user for hostel ───────────────────────────────────────
    data = {
        "complaint_text": complaint_text,
        "category":       category,
        "title":          title,
        "needs_room":     needs_room,
        "staff_role":     staff_role,
        "hostel_id":      None,
        "hostel_name":    None,
        "room_number":    None,
    }
    _set_session(chat_id, STATE_AWAITING_HOSTEL, data)
    logger.info(
        f"[ComplaintDialogue] Session started chat_id={chat_id} category={category}"
    )

    # Fetch real hostel names from DB for the example hint
    try:
        hostels = complaint_repo.get_all_hostels()
        hostel_example = ", ".join(h.get("name", "") for h in hostels[:4])
        if len(hostels) > 4:
            hostel_example += "…"
    except Exception:
        hostel_example = "e.g. Hostel 1, Hostel 2"

    category_label = category.capitalize()
    return (
        f"I understand — that sounds like a **{category_label}** issue. "
        f"I'll help you file a formal complaint right away! 📋\n\n"
        f"**Which hostel are you staying in?**\n"
        f"_({hostel_example}  |  or type 'cancel' to abort)_"
    )


def handle_complaint_turn(
    chat_id: str,
    user_message: str,
    user_info: Dict[str, Any],
) -> Optional[str]:
    """
    Process one user turn within an active complaint session.
    Returns the bot's next response string, or None if no active session.
    """
    session = _get_session(chat_id)
    if not session:
        return None  # No active session — caller falls back to RAG

    state = session["state"]
    data  = session["data"]

    # ── Cancellation ──────────────────────────────────────────────────────────
    user_lower = user_message.lower().strip()
    if any(kw in user_lower for kw in CANCEL_KEYWORDS):
        _clear_session(chat_id)
        return (
            "No problem! Your complaint has been cancelled. 😊 "
            "Feel free to ask me anything else about campus."
        )

    # ── State: awaiting hostel ─────────────────────────────────────────────────
    if state == STATE_AWAITING_HOSTEL:
        hostels = complaint_repo.get_all_hostels()
        matched = _fuzzy_match_hostel(user_message, hostels)

        if not matched:
            hostel_names = ", ".join(h.get("name", "") for h in hostels)
            return (
                f"I couldn't find that hostel. Please check the name.\n\n"
                f"**Available hostels:** {hostel_names}."
            )

        data["hostel_id"]   = matched["id"]
        data["hostel_name"] = matched.get("name", user_message)

        if data.get("needs_room"):
            _set_session(chat_id, STATE_AWAITING_ROOM, data)
            return (
                f"Got it — **{data['hostel_name']}** hostel ✅\n\n"
                f"**What is your room number?**\n_(e.g. 204, A-12)_"
            )
        else:
            return _submit_and_respond(chat_id, data, user_info)

    # ── State: awaiting room ───────────────────────────────────────────────────
    if state == STATE_AWAITING_ROOM:
        room = user_message.strip()

        # Detect hostel correction: user is clarifying/correcting the hostel, not giving a room
        correction_signals = [
            "hostel", "not girls", "not boys", "i said", "i meant", "it is", "it's",
            "my hostel", "wrong hostel", "no no", "actually",
        ]
        is_correction = any(sig in user_lower for sig in correction_signals)
        if is_correction:
            # Re-run hostel matching on the correction message
            hostels = complaint_repo.get_all_hostels()
            matched = _fuzzy_match_hostel(user_message, hostels)
            if matched:
                data["hostel_id"]   = matched["id"]
                data["hostel_name"] = matched.get("name", user_message)
                if data.get("needs_room"):
                    _set_session(chat_id, STATE_AWAITING_ROOM, data)
                    return (
                        f"Got it, corrected to **{data['hostel_name']}** hostel ✅\n\n"
                        f"**What is your room number?** _(e.g. 204, A-12)_"
                    )
                else:
                    return _submit_and_respond(chat_id, data, user_info)
            else:
                hostel_names = ", ".join(h.get("name", "") for h in hostels)
                return (
                    f"I still couldn't find that hostel.\n\n"
                    f"**Available hostels:** {hostel_names}."
                )

        if len(room) > 15 or not re.search(r"[A-Za-z0-9]", room):
            return (
                "That doesn't look like a valid room number. "
                "Please re-enter it. _(e.g. 204, A-12)_"
            )
        data["room_number"] = room
        return _submit_and_respond(chat_id, data, user_info)

    # Unknown state — clear and return None so caller falls back to RAG
    _clear_session(chat_id)
    return None


def _submit_and_respond(
    chat_id: str,
    data: Dict[str, Any],
    user_info: Dict[str, Any],
) -> str:
    """Submit the gathered complaint to the DB and return a confirmation message."""
    try:
        result = process_complaint(
            text=data["complaint_text"],
            user_info=user_info,
            hostel_id=data.get("hostel_id"),
            room_number=data.get("room_number"),
        )
        _clear_session(chat_id)

        if result.get("error"):
            return (
                "⚠️ I wasn't able to file that complaint right now. "
                "Please try again or contact the administration directly."
            )

        complaint_row = result.get("complaint", {})
        complaint_id  = complaint_row.get("id", "N/A")
        title         = result.get("title", data.get("title", "Your complaint"))
        category      = result.get("category", data.get("category", "general")).capitalize()
        hostel_name   = data.get("hostel_name") or "your hostel"
        room_number   = data.get("room_number")
        staff_role    = data.get("staff_role") or ""

        staff_label_map = {
            "electrical":   "hostel electrician ⚡",
            "cleaning":     "housekeeping staff 🧹",
            "mess_manager": "mess manager 🍽️",
            "watchmen":     "hostel security 🔒",
        }
        staff_display = staff_label_map.get(staff_role, "the relevant staff member")
        location = hostel_name + (f", Room {room_number}" if room_number else "")

        similar = result.get("similar", [])
        similar_note = ""
        if similar:
            similar_note = (
                f"\n\n📌 **{len(similar)} similar open complaint(s)** are already on record — "
                f"the administration is aware of this issue."
            )

        return (
            f"✅ **Complaint Filed Successfully!**\n\n"
            f"**Title:** {title}\n"
            f"**Category:** {category}\n"
            f"**Location:** {location}\n"
            f"**Complaint ID:** `{complaint_id}`\n\n"
            f"Your complaint has been forwarded to {staff_display}. "
            f"Track its status anytime via **My Complaints** in the sidebar."
            f"{similar_note}"
        )

    except Exception as e:
        logger.error(f"[ComplaintDialogue] Submission error: {e}")
        _clear_session(chat_id)
        return (
            "⚠️ Something went wrong while filing your complaint. "
            "Please try again or report it to the administration directly."
        )
