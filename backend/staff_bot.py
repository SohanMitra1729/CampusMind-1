"""
staff_bot.py — Dedicated Telegram Bot for Staff Members
────────────────────────────────────────────────────────
Staff roles supported: electrical | cleaning | mess_manager | watchmen

Registration flow:
  1. /start  → ask for phone number
  2. Show hostel list (from DB) → user picks one
  3. Show role options → user picks one
  4. Save to staff_members table

Complaint forwarding:
  - send_complaint_to_staff(complaint_row, hostel_id, room_number, category, supabase)
    routes to all active staff matching role + hostel, with ack/resolve inline buttons.
"""

import os
import re
import json
import requests
import httpx
from typing import Optional, Dict, Any, List

from app.core.config import settings

STAFF_BOT_TOKEN = settings.STAFF_BOT_TOKEN or ""
STAFF_TELEGRAM_API = f"https://api.telegram.org/bot{STAFF_BOT_TOKEN}"

# ── Role mapping: complaint category → staff role ─────────────────────────────
CATEGORY_TO_ROLE: Dict[str, str] = {
    "facility":  "electrical",    # electrical / maintenance issues
    "hostel":    "watchmen",      # general hostel issues → watchmen
    "mess":      "mess_manager",  # food/mess issues → mess manager
    "general":   "cleaning",      # general/cleanliness → cleaning (fallback)
}

ROLE_ICONS: Dict[str, str] = {
    "electrical":    "⚡",
    "cleaning":      "🧹",
    "mess_manager":  "🍽️",
    "watchmen":      "🔒",
}

ROLE_LABELS: Dict[str, str] = {
    "electrical":   "Electrical / Maintenance",
    "cleaning":     "Cleaning Staff",
    "mess_manager": "Mess Manager",
    "watchmen":     "Watchmen / Security",
}

# In-memory registration state per chat_id
# State values: None | "awaiting_phone" | "awaiting_hostel" | "awaiting_role"
_staff_state: Dict[str, Dict[str, Any]] = {}


# ── Telegram helpers ──────────────────────────────────────────────────────────

def _send(chat_id: str, text: str, parse_mode: str = "Markdown",
          reply_markup: Optional[Dict] = None):
    """Send a message via the Staff Bot."""
    if not STAFF_BOT_TOKEN:
        print("[StaffBot] STAFF_BOT_TOKEN not set. Message not sent.")
        return
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(f"{STAFF_TELEGRAM_API}/sendMessage", json=payload, timeout=5)
    except Exception as e:
        print(f"[StaffBot] send error: {e}")


def _answer_callback(callback_query_id: str, text: str = ""):
    """Answer a callback_query to remove the loading spinner."""
    if not STAFF_BOT_TOKEN:
        return
    try:
        requests.post(
            f"{STAFF_TELEGRAM_API}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": text},
            timeout=5,
        )
    except Exception as e:
        print(f"[StaffBot] answer_callback error: {e}")


def _edit_message_text(chat_id: str, message_id: int, text: str, parse_mode: str = "Markdown"):
    """Edit a previously sent message."""
    if not STAFF_BOT_TOKEN:
        return
    try:
        requests.post(
            f"{STAFF_TELEGRAM_API}/editMessageText",
            json={"chat_id": chat_id, "message_id": message_id,
                  "text": text, "parse_mode": parse_mode},
            timeout=5,
        )
    except Exception as e:
        print(f"[StaffBot] edit_message error: {e}")


# ── Hostel keyboard builder ───────────────────────────────────────────────────

def _hostel_keyboard(hostels: List[Dict]) -> Dict:
    """Build an inline keyboard of hostel buttons (2 per row)."""
    buttons = []
    row = []
    for h in hostels:
        row.append({"text": f"{h['code']} – {h['name']}", "callback_data": f"hostel:{h['id']}:{h['code']}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return {"inline_keyboard": buttons}


def _role_keyboard() -> Dict:
    """Build an inline keyboard for the four staff roles."""
    buttons = [
        [{"text": f"{ROLE_ICONS['electrical']} Electrical / Maintenance",
          "callback_data": "role:electrical"}],
        [{"text": f"{ROLE_ICONS['cleaning']} Cleaning Staff",
          "callback_data": "role:cleaning"}],
        [{"text": f"{ROLE_ICONS['mess_manager']} Mess Manager",
          "callback_data": "role:mess_manager"}],
        [{"text": f"{ROLE_ICONS['watchmen']} Watchmen / Security",
          "callback_data": "role:watchmen"}],
    ]
    return {"inline_keyboard": buttons}


# ── Registration flow ─────────────────────────────────────────────────────────

def _start_registration(chat_id: str):
    _staff_state[chat_id] = {"step": "awaiting_phone"}
    _send(chat_id, (
        "👋 Welcome to *CampusMind Staff Portal*!\n\n"
        "To register, please share your phone number (e.g. *+919876543210*):"
    ))


def _handle_phone(chat_id: str, text: str, supabase):
    phone = text.strip()
    # Basic E.164-ish validation
    if not re.match(r"^\+?\d{10,15}$", phone):
        _send(chat_id, "⚠️ Invalid phone number. Please enter a valid number (e.g. +919876543210):")
        return
    _staff_state[chat_id]["phone"] = phone
    _staff_state[chat_id]["step"] = "awaiting_hostel"

    # Fetch hostels from DB
    try:
        res = supabase.table("hostels").select("id, name, code").order("code").execute()
        hostels = res.data or []
    except Exception:
        hostels = []

    if not hostels:
        _send(chat_id, "⚠️ No hostels found in the system. Please contact administration.")
        _staff_state.pop(chat_id, None)
        return

    _staff_state[chat_id]["hostels"] = hostels
    _send(chat_id, "🏠 Which hostel do you work at?", reply_markup=_hostel_keyboard(hostels))


def _handle_hostel_callback(chat_id: str, hostel_id: str, hostel_code: str):
    state = _staff_state.get(chat_id, {})
    state["hostel_id"] = hostel_id
    state["hostel_code"] = hostel_code
    state["step"] = "awaiting_role"
    _staff_state[chat_id] = state
    _send(chat_id, f"✅ Hostel *{hostel_code}* selected.\n\n🔧 What is your role?",
          reply_markup=_role_keyboard())


def _handle_role_callback(chat_id: str, role: str, supabase):
    state = _staff_state.get(chat_id, {})
    phone = state.get("phone")
    hostel_id = state.get("hostel_id")
    hostel_code = state.get("hostel_code", "")

    if not phone or not hostel_id:
        _send(chat_id, "⚠️ Registration session expired. Please send /start to begin again.")
        _staff_state.pop(chat_id, None)
        return

    try:
        # Upsert into staff_members on phone_number conflict
        supabase.table("staff_members").upsert({
            "phone_number":     phone,
            "telegram_chat_id": str(chat_id),
            "role":             role,
            "hostel_id":        hostel_id,
            "active":           True,
        }, on_conflict="phone_number").execute()

        _staff_state.pop(chat_id, None)
        role_label = ROLE_LABELS.get(role, role)
        role_icon  = ROLE_ICONS.get(role, "🔧")
        _send(chat_id, (
            f"✅ *Registration complete!*\n\n"
            f"{role_icon} Role: *{role_label}*\n"
            f"🏠 Hostel: *{hostel_code}*\n\n"
            f"You will receive complaint notifications here when students report issues "
            f"matching your role and hostel.\n\n"
            f"Commands:\n"
            f"• /mystatus — View your registration\n"
            f"• /start — Update registration"
        ))
    except Exception as e:
        print(f"[StaffBot] registration error: {e}")
        _send(chat_id, "❌ Registration failed. Please try again with /start.")
        _staff_state.pop(chat_id, None)


def _handle_my_status(chat_id: str, supabase):
    try:
        res = (
            supabase.table("staff_members")
            .select("role, hostel_id, phone_number, active, hostels(name, code)")
            .eq("telegram_chat_id", str(chat_id))
            .single()
            .execute()
        )
        if not res.data:
            _send(chat_id, "⚠️ You are not registered. Please send /start to register.")
            return
        d = res.data
        hostel_name = d.get("hostels", {}).get("name", "Unknown") if d.get("hostels") else "Unknown"
        hostel_code = d.get("hostels", {}).get("code", "") if d.get("hostels") else ""
        role = d.get("role", "unknown")
        active = "✅ Active" if d.get("active") else "❌ Inactive"
        _send(chat_id, (
            f"👤 *Your Staff Profile*\n\n"
            f"{ROLE_ICONS.get(role, '🔧')} Role: *{ROLE_LABELS.get(role, role)}*\n"
            f"🏠 Hostel: *{hostel_code} – {hostel_name}*\n"
            f"📞 Phone: {d.get('phone_number', 'N/A')}\n"
            f"Status: {active}\n\n"
            f"To update, send /start again."
        ))
    except Exception as e:
        print(f"[StaffBot] _handle_my_status error: {e}")
        _send(chat_id, "❌ Could not fetch your profile.")


# ── Complaint forwarding (called from complaint_agent.py) ─────────────────────

def send_complaint_to_staff(
    complaint_id: str,
    title: str,
    description: str,
    category: str,
    hostel_id: Optional[str],
    hostel_name: str,
    room_number: Optional[str],
    student_name: str,
    supabase,
    staff_role: Optional[str] = None,   # LLM-determined role; falls back to CATEGORY_TO_ROLE
):
    """
    Find all active staff matching the complaint's role and hostel,
    then send a formatted notification with Ack / Resolve inline buttons.

    Two-pass hostel strategy:
      Pass 1: role + hostel_id (exact match)
      Pass 2: role only (no hostel filter) — fallback when no exact match found
    """
    if not STAFF_BOT_TOKEN:
        print("[StaffBot] STAFF_BOT_TOKEN not set. Complaint not forwarded.")
        return

    # Determine required staff role — prefer LLM-determined, fall back to category table
    role = staff_role or CATEGORY_TO_ROLE.get(category, "watchmen")
    if not role:
        print(f"[StaffBot] No staff role determined for category={category}. Skipping forward.")
        return

    print(f"[StaffBot] Routing complaint to role={role} (staff_role={staff_role}, category={category})")

    # ── Pass 1: Match by role AND hostel ──────────────────────────────────────
    staff_list = []
    try:
        query = (
            supabase.table("staff_members")
            .select("telegram_chat_id, role, hostel_id")
            .eq("role", role)
            .eq("active", True)
        )
        if hostel_id:
            query = query.eq("hostel_id", hostel_id)
        res = query.execute()
        staff_list = res.data or []
        print(f"[StaffBot] Pass 1 (role={role}, hostel={hostel_id}): found {len(staff_list)} staff")
    except Exception as e:
        print(f"[StaffBot] staff query error (pass 1): {e}")

    # ── Pass 2: Fallback — match by role only (any hostel) ───────────────────
    if not staff_list and hostel_id:
        try:
            res2 = (
                supabase.table("staff_members")
                .select("telegram_chat_id, role, hostel_id")
                .eq("role", role)
                .eq("active", True)
                .execute()
            )
            staff_list = res2.data or []
            print(f"[StaffBot] Pass 2 fallback (role={role}, any hostel): found {len(staff_list)} staff")
        except Exception as e:
            print(f"[StaffBot] staff query error (pass 2): {e}")

    if not staff_list:
        print(f"[StaffBot] No active staff found for role={role} in any hostel. Cannot forward complaint.")
        return

    # Build message
    location_line = f"🏠 Hostel: *{hostel_name}*"
    if room_number:
        location_line += f"  |  🚪 Room: *{room_number}*"

    cat_icon = {
        "hostel": "🏠", "mess": "🍽️", "facility": "🔧",
        "academic": "📚", "transport": "🚌", "general": "📢",
    }.get(category, "📢")

    msg = (
        f"🚨 *New Complaint Assigned*\n\n"
        f"{cat_icon} Category: *{category.capitalize()}*\n"
        f"{location_line}\n"
        f"👤 Student: {student_name}\n\n"
        f"*{title}*\n"
        f"_{description[:300]}{'…' if len(description) > 300 else ''}_\n\n"
        f"Please acknowledge or resolve below 👇"
    )

    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Acknowledged", "callback_data": f"staff_ack:{complaint_id}"},
            {"text": "✔️ Resolved",     "callback_data": f"staff_resolve:{complaint_id}"},
        ]]
    }

    for staff in staff_list:
        chat_id = staff.get("telegram_chat_id")
        if chat_id:
            _send(chat_id, msg, reply_markup=keyboard)

    print(f"[StaffBot] Complaint {complaint_id} forwarded to {len(staff_list)} staff member(s).")


# ── Callback handler for Ack / Resolve ───────────────────────────────────────

def _handle_staff_callback(chat_id: str, callback_data: str, callback_query_id: str,
                            message_id: int, supabase):
    parts = callback_data.split(":")
    if len(parts) != 2:
        return

    action, complaint_id = parts[0], parts[1]
    new_status = "in_progress" if action == "staff_ack" else "resolved"
    action_label = "Acknowledged 👍" if action == "staff_ack" else "Marked as Resolved ✅"

    try:
        res = (
            supabase.table("complaints")
            .update({"status": new_status})
            .eq("id", complaint_id)
            .execute()
        )
        if res.data:
            _answer_callback(callback_query_id, action_label)
            _edit_message_text(
                chat_id, message_id,
                f"✅ *{action_label}*\n\nComplaint ID: `{complaint_id}`\nStatus updated to *{new_status.replace('_', ' ').title()}*."
            )
        else:
            _answer_callback(callback_query_id, "Complaint not found.")
    except Exception as e:
        print(f"[StaffBot] callback update error: {e}")
        _answer_callback(callback_query_id, "Error updating complaint.")


# ── Main update handler ───────────────────────────────────────────────────────

def handle_staff_update(update: dict, supabase):
    """
    Entry point called from FastAPI staff webhook endpoint.
    Routes messages and callback_queries to the correct handler.
    """
    # Handle callback_query (button presses)
    callback = update.get("callback_query")
    if callback:
        chat_id          = str(callback.get("from", {}).get("id", ""))
        callback_data    = callback.get("data", "")
        callback_query_id = callback.get("id", "")
        message_id       = callback.get("message", {}).get("message_id", 0)

        if callback_data.startswith("hostel:"):
            parts = callback_data.split(":")
            _handle_hostel_callback(chat_id, parts[1], parts[2])
        elif callback_data.startswith("role:"):
            _handle_role_callback(chat_id, callback_data.split(":")[1], supabase)
        elif callback_data.startswith("staff_ack:") or callback_data.startswith("staff_resolve:"):
            _handle_staff_callback(chat_id, callback_data, callback_query_id, message_id, supabase)
        return

    # Handle regular messages
    message = update.get("message")
    if not message:
        return

    chat_id = str(message.get("chat", {}).get("id", ""))
    text    = message.get("text", "").strip()

    if not chat_id or not text:
        return

    print(f"[StaffBot] Message from {chat_id}: {text[:60]}")

    state = _staff_state.get(chat_id, {})

    # State-based handlers
    if state.get("step") == "awaiting_phone":
        _handle_phone(chat_id, text, supabase)
        return

    # Command handlers
    if text.startswith("/start"):
        _start_registration(chat_id)
        return

    if text.startswith("/mystatus"):
        _handle_my_status(chat_id, supabase)
        return

    if text.startswith("/help"):
        _send(chat_id, (
            "🔧 *Staff Bot Commands*\n\n"
            "/start — Register or update your profile\n"
            "/mystatus — View your current registration\n"
            "/help — Show this message\n\n"
            "You will automatically receive complaint alerts based on your role and hostel."
        ))
        return

    # Default
    _send(chat_id, "ℹ️ Use /start to register or /mystatus to view your profile.")


# ── Webhook setup ─────────────────────────────────────────────────────────────

async def setup_staff_webhook():
    """Called on FastAPI startup to register the staff bot webhook."""
    webhook_url = settings.STAFF_BOT_WEBHOOK_URL or ""
    if not STAFF_BOT_TOKEN or not webhook_url:
        print("[StaffBot] STAFF_BOT_TOKEN or STAFF_BOT_WEBHOOK_URL not set. Skipping webhook setup.")
        return
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{STAFF_TELEGRAM_API}/setWebhook",
                json={"url": webhook_url}
            )
            res.raise_for_status()
            print(f"[StaffBot] Webhook registered: {res.json()}")
    except Exception as e:
        print(f"[StaffBot] Failed to set webhook: {e}")
