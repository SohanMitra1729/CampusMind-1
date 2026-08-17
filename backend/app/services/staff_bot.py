"""
app/services/staff_bot.py — Dedicated Telegram Bot for Staff Members
────────────────────────────────────────────────────────────────────
Staff roles supported: electrical | cleaning | mess_manager | watchmen
Features DB-backed persistent session state and httpx communication.
"""

import os
import re
import json
import httpx
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.core.logger import logger
from app.db.supabase import supabase

STAFF_BOT_TOKEN = settings.STAFF_BOT_TOKEN or ""
STAFF_TELEGRAM_API = f"https://api.telegram.org/bot{STAFF_BOT_TOKEN}"

CATEGORY_TO_ROLE: Dict[str, str] = {
    "facility":  "electrical",
    "hostel":    "watchmen",
    "mess":      "mess_manager",
    "general":   "cleaning",
}

ROLE_ICONS: Dict[str, str] = {
    "electrical":    "⚡",
    "cleaning":      "🧹",
    "maintenance":   "🛠️",
    "mess_manager":  "🍽️",
    "watchmen":      "🔒",
}

ROLE_LABELS: Dict[str, str] = {
    "electrical":   "Electrical / Maintenance",
    "cleaning":     "Cleaning Staff",
    "maintenance":  "Maintenance (Furniture / Plumbing / Civil)",
    "mess_manager": "Mess Manager",
    "watchmen":     "Watchmen / Security",
}

_staff_state_fallback: Dict[str, Dict[str, Any]] = {}


# ── DB-backed Persistent Session Helpers ───────────────────────────────────────

def _get_staff_state(chat_id: str) -> Dict[str, Any]:
    """Retrieve active session state for staff chat_id."""
    try:
        res = supabase.table("bot_sessions").select("data").eq("chat_id", f"staff:{chat_id}").execute()
        if res.data and res.data[0]:
            return res.data[0].get("data") or {}
    except Exception:
        pass
    return _staff_state_fallback.get(str(chat_id), {})


def _set_staff_state(chat_id: str, state_dict: Optional[Dict[str, Any]]):
    """Set or clear active staff registration state."""
    key = str(chat_id)
    if state_dict is None:
        _staff_state_fallback.pop(key, None)
        try:
            supabase.table("bot_sessions").delete().eq("chat_id", f"staff:{key}").execute()
        except Exception:
            pass
    else:
        _staff_state_fallback[key] = state_dict
        try:
            supabase.table("bot_sessions").upsert({
                "chat_id": f"staff:{key}",
                "state": state_dict.get("step"),
                "data": state_dict,
            }, on_conflict="chat_id").execute()
        except Exception:
            pass


def _send(chat_id: str, text: str, parse_mode: str = "Markdown",
          reply_markup: Optional[Dict] = None):
    if not STAFF_BOT_TOKEN:
        logger.info("[StaffBot] STAFF_BOT_TOKEN not set. Message not sent.")
        return
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(f"{STAFF_TELEGRAM_API}/sendMessage", json=payload)
    except Exception as e:
        logger.error(f"[StaffBot] send error: {e}")


def _answer_callback(callback_query_id: str, text: str = ""):
    if not STAFF_BOT_TOKEN:
        return
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(
                f"{STAFF_TELEGRAM_API}/answerCallbackQuery",
                json={"callback_query_id": callback_query_id, "text": text},
            )
    except Exception as e:
        logger.error(f"[StaffBot] answer_callback error: {e}")


def _edit_message_text(chat_id: str, message_id: int, text: str, parse_mode: str = "Markdown"):
    if not STAFF_BOT_TOKEN:
        return
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(
                f"{STAFF_TELEGRAM_API}/editMessageText",
                json={"chat_id": chat_id, "message_id": message_id,
                      "text": text, "parse_mode": parse_mode},
            )
    except Exception as e:
        logger.error(f"[StaffBot] edit_message error: {e}")


def _hostel_keyboard(hostels: List[Dict]) -> Dict:
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
    buttons = [
        [{"text": f"{ROLE_ICONS['electrical']} Electrical / Maintenance",
          "callback_data": "role:electrical"}],
        [{"text": f"{ROLE_ICONS['cleaning']} Cleaning Staff",
          "callback_data": "role:cleaning"}],
        [{"text": f"{ROLE_ICONS['maintenance']} Maintenance (Furniture / Plumbing)",
          "callback_data": "role:maintenance"}],
        [{"text": f"{ROLE_ICONS['mess_manager']} Mess Manager",
          "callback_data": "role:mess_manager"}],
        [{"text": f"{ROLE_ICONS['watchmen']} Watchmen / Security",
          "callback_data": "role:watchmen"}],
    ]
    return {"inline_keyboard": buttons}


def _start_registration(chat_id: str):
    _set_staff_state(chat_id, {"step": "awaiting_phone"})
    _send(chat_id, (
        "👋 Welcome to *CampusMind Staff Portal*!\n\n"
        "To register, please share your phone number (e.g. *+919876543210*):"
    ))


def _handle_phone(chat_id: str, text: str, _db=None):
    phone = text.strip()
    if not re.match(r"^\+?\d{10,15}$", phone):
        _send(chat_id, "⚠️ Invalid phone number. Please enter a valid number (e.g. +919876543210):")
        return
    
    state = _get_staff_state(chat_id)
    state["phone"] = phone
    state["step"] = "awaiting_hostel"

    try:
        res = supabase.table("hostels").select("id, name, code").order("code").execute()
        hostels = res.data or []
    except Exception:
        hostels = []

    if not hostels:
        _send(chat_id, "⚠️ No hostels found in the system. Please contact administration.")
        _set_staff_state(chat_id, None)
        return

    state["hostels"] = hostels
    _set_staff_state(chat_id, state)
    _send(chat_id, "🏠 Which hostel do you work at?", reply_markup=_hostel_keyboard(hostels))


def _handle_hostel_callback(chat_id: str, hostel_id: str, hostel_code: str):
    state = _get_staff_state(chat_id)
    state["hostel_id"] = hostel_id
    state["hostel_code"] = hostel_code
    state["step"] = "awaiting_role"
    _set_staff_state(chat_id, state)
    _send(chat_id, f"✅ Hostel *{hostel_code}* selected.\n\n🔧 What is your role?",
          reply_markup=_role_keyboard())


def _handle_role_callback(chat_id: str, role: str, _db=None):
    state = _get_staff_state(chat_id)
    phone = state.get("phone")
    hostel_id = state.get("hostel_id")
    hostel_code = state.get("hostel_code", "")

    if not phone or not hostel_id:
        _send(chat_id, "⚠️ Registration session expired. Please send /start to begin again.")
        _set_staff_state(chat_id, None)
        return

    try:
        supabase.table("staff_members").upsert({
            "phone_number":     phone,
            "telegram_chat_id": str(chat_id),
            "role":             role,
            "hostel_id":        hostel_id,
            "active":           True,
        }, on_conflict="phone_number").execute()

        _set_staff_state(chat_id, None)
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
        logger.error(f"[StaffBot] registration error: {e}")
        _send(chat_id, "❌ Registration failed. Please try again with /start.")
        _set_staff_state(chat_id, None)


def _handle_my_status(chat_id: str, _db=None):
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
        logger.error(f"[StaffBot] _handle_my_status error: {e}")
        _send(chat_id, "❌ Could not fetch your profile.")


def send_complaint_to_staff(
    complaint_id: str,
    title: str,
    description: str,
    category: str,
    hostel_id: Optional[str],
    hostel_name: str,
    room_number: Optional[str],
    student_name: str,
    _db=None,
    staff_role: Optional[str] = None,
    scope: Optional[str] = None,
    mess_id: Optional[str] = None,
):
    if not STAFF_BOT_TOKEN:
        logger.info("[StaffBot] STAFF_BOT_TOKEN not set. Complaint not forwarded.")
        return

    # ── Categories not handled by hostel staff — do NOT misroute to watchmen ──
    NON_HOSTEL_CATEGORIES = {"academic", "admin", "transport"}
    if category in NON_HOSTEL_CATEGORIES:
        logger.info(
            f"[StaffBot] Skipping forward: category={category} is not handled by hostel staff. "
            f"staff_role={staff_role}. No Telegram notification sent."
        )
        return

    # ── Determine role: LLM assignment takes priority; fallback to category map ──
    if not staff_role or staff_role == "none":
        role = CATEGORY_TO_ROLE.get(category)
        if not role:
            logger.info(
                f"[StaffBot] No staff role determined for category={category}. Skipping forward."
            )
            return
    else:
        role = staff_role

    logger.info(f"[StaffBot] Routing complaint to role={role} (scope={scope}, mess_id={mess_id}, hostel={hostel_id})")

    staff_list = []
    try:
        query = (
            supabase.table("staff_members")
            .select("telegram_chat_id, role, hostel_id, mess_id")
            .eq("role", role)
            .eq("active", True)
        )
        # For mess managers, match by mess_id if available, otherwise hostel_id
        if role == "mess_manager" and mess_id:
            query = query.eq("mess_id", mess_id)
        elif hostel_id:
            query = query.eq("hostel_id", hostel_id)

        res = query.execute()
        staff_list = res.data or []
        logger.info(f"[StaffBot] Pass 1 (role={role}, hostel={hostel_id}, mess_id={mess_id}): found {len(staff_list)} staff")
    except Exception as e:
        logger.error(f"[StaffBot] staff query error (pass 1): {e}")

    if not staff_list and (hostel_id or mess_id):
        try:
            res2 = (
                supabase.table("staff_members")
                .select("telegram_chat_id, role, hostel_id, mess_id")
                .eq("role", role)
                .eq("active", True)
                .execute()
            )
            staff_list = res2.data or []
            logger.info(f"[StaffBot] Pass 2 fallback (role={role}, any hostel): found {len(staff_list)} staff")
        except Exception as e:
            logger.error(f"[StaffBot] staff query error (pass 2): {e}")

    if not staff_list:
        logger.warning(f"[StaffBot] No active staff found for role={role} in any hostel. Cannot forward complaint.")
        return

    location_line = f"🏠 Facility: *{hostel_name}*"
    if room_number:
        location_line += f"  |  🚪 Room: *{room_number}*"

    cat_icon = {
        "hostel": "🏠", "mess": "🍽️", "facility": "🔧",
        "academic": "📚", "transport": "🚌", "general": "📢",
    }.get(category, "📢")

    role_label = ROLE_LABELS.get(role, role)
    role_icon  = ROLE_ICONS.get(role, "🔧")

    scope_display = {
        "MESS": "🍽️ Dining / Mess",
        "ROOM_SHARED": "👥 Room (Shared Fixture)",
        "ROOM_INDIVIDUAL": "👤 Personal Item",
        "COMMON_AREA": "🏢 Common / Floor Area",
    }.get(scope, "🏢 General")

    msg = (
        f"🚨 *New Complaint Assigned*\n\n"
        f"{cat_icon} Category: *{category.capitalize()}* ({scope_display})\n"
        f"{role_icon} Assigned To: *{role_label}*\n"
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

    logger.info(f"[StaffBot] Complaint {complaint_id} forwarded to {len(staff_list)} staff member(s).")


def _handle_staff_callback(chat_id: str, callback_data: str, callback_query_id: str,
                            message_id: int, _db=None):
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
        logger.error(f"[StaffBot] callback update error: {e}")
        _answer_callback(callback_query_id, "Error updating complaint.")


def handle_staff_update(update: dict, _db=None):
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
            _handle_role_callback(chat_id, callback_data.split(":")[1])
        elif callback_data.startswith("staff_ack:") or callback_data.startswith("staff_resolve:"):
            _handle_staff_callback(chat_id, callback_data, callback_query_id, message_id)
        return

    message = update.get("message")
    if not message:
        return

    chat_id = str(message.get("chat", {}).get("id", ""))
    text    = message.get("text", "").strip()

    if not chat_id or not text:
        return

    logger.info(f"[StaffBot] Message from {chat_id}: {text[:60]}")

    state = _get_staff_state(chat_id)

    if state.get("step") == "awaiting_phone":
        _handle_phone(chat_id, text)
        return

    if text.startswith("/start"):
        _start_registration(chat_id)
        return

    if text.startswith("/mystatus"):
        _handle_my_status(chat_id)
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

    _send(chat_id, "ℹ️ Use /start to register or /mystatus to view your profile.")


async def setup_staff_webhook():
    webhook_url = settings.STAFF_BOT_WEBHOOK_URL or ""
    if not STAFF_BOT_TOKEN or not webhook_url:
        logger.info("[StaffBot] STAFF_BOT_TOKEN or STAFF_BOT_WEBHOOK_URL not set. Skipping webhook setup.")
        return
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{STAFF_TELEGRAM_API}/setWebhook",
                json={"url": webhook_url}
            )
            res.raise_for_status()
            logger.info(f"[StaffBot] Webhook registered: {res.json()}")
    except Exception as e:
        logger.error(f"[StaffBot] Failed to set webhook: {e}")
