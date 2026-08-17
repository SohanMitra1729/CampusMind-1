"""
app/services/complaint_agent.py — Agentic Complaint Management Pipeline
────────────────────────────────────────────────────────────────────────
4-stage funnel:
  Stage 1: CLASSIFY  — LLM determines complaint, category, staff_role, scope & checks for semantic duplicate of active tickets
  Stage 2: ENRICH    — If hostel/mess related, resolve hostel details & mess_id from DB
  Stage 3: SPAM/SIMILAR — Check for student self-duplicates & scope-aware similar tickets
  Stage 4: INGEST    — Save with permanent scope/role & dispatch to ground staff
"""

import re
import os
import json
from typing import Optional, List, Dict, Any

from app.core.config import settings
from app.core.key_pool import groq_pool
import app.repositories.document_repository as doc_repo
import app.repositories.complaint_repository as complaint_repo

from app.core.logger import logger

COMPLAINT_CATEGORIES = {
    "hostel", "academic", "admin", "facility", "mess", "transport", "general",
}

CATEGORY_ICONS = {
    "hostel":    "🏠",
    "academic":  "📚",
    "admin":     "🏛️",
    "facility":  "🔧",
    "mess":      "🍽️",
    "transport": "🚌",
    "general":   "📢",
}

STATUS_LABELS = {
    "open":        ("🔴", "Open"),
    "in_progress": ("🟡", "In Progress"),
    "resolved":    ("🟢", "Resolved"),
    "dismissed":   ("⚫", "Dismissed"),
}


# ── Stage 1: Classify ─────────────────────────────────────────────────────────

def classify_complaint(text: str, active_tickets: Optional[List[Dict[str, Any]]] = None) -> dict:
    """Determine if the input text is a complaint, extract category, role, boundary scope, and check for semantic duplicate."""
    excerpt = text[:400].strip()

    active_tickets_context = ""
    if active_tickets:
        active_tickets_context = "\nStudent's currently ACTIVE open tickets:\n"
        for t in active_tickets:
            t_id = t.get("id", "")
            active_tickets_context += f"- Ticket ID: \"{t_id}\" | Title: \"{t.get('title')}\" | Desc: \"{(t.get('description') or '')[:80]}\" | Status: {t.get('status')}\n"
        active_tickets_context += (
            "\nSEMANTIC DUPLICATE CHECK RULE:\n"
            "If the student message refers to the EXACT SAME root problem/incident as one of the active tickets above "
            "(even with completely different wording/synonyms, e.g. 'no hot water' vs 'geyser broken', 'dark room' vs 'light fused', 'bad food' vs 'stale dinner', 'fan not spinning' vs 'fan dead'), "
            "set 'duplicate_of_id' to that exact Ticket ID. Otherwise set 'duplicate_of_id' to null.\n"
        )

    prompt = f"""You are a complaint classifier for a university student portal.

Student message:
\"\"\"{excerpt}\"\"\"{active_tickets_context}

Respond with a single JSON object only (no markdown):
{{
  "is_complaint": <true if this is a complaint/grievance/problem, false if it is a general question>,
  "category": "<hostel|academic|admin|facility|mess|transport|general|not_complaint>",
  "title": "<short complaint title max 60 chars, empty string if not a complaint>",
  "confidence": <0.0-1.0>,
  "needs_room": <true if the complaint is about a specific room fixture or personal item in a room, false if it is mess/campus/corridor/common>,
  "staff_role": "<which staff role should handle this: electrical | cleaning | maintenance | mess_manager | watchmen | none>",
  "scope": "<MESS | ROOM_SHARED | ROOM_INDIVIDUAL | COMMON_AREA>",
  "duplicate_of_id": <exact Ticket ID string if duplicate of an active ticket, otherwise null>
}}

staff_role rules:
- electrical  : lights, fans, power, switches, sockets, electrical fittings, wiring, inverter, generator, short circuit
- cleaning    : garbage, cleanliness, dirty bathroom, waste, sweeping, mopping, sanitation, cockroaches, pest control, bad smell
- maintenance : broken/damaged furniture (bed, mattress, study table, chair, wardrobe, shelf), plumbing (tap leaking, pipe burst, drain blocked, flush broken, shower not working), broken door, broken window, broken lock, ceiling crack, wall damage, civil/structural issues
- mess_manager: food quality, meal timing, mess hygiene, canteen, water in mess, dining, raw/stale food
- watchmen    : security, entry/exit, gate, theft, outsiders, curfew, general hostel safety, stranger
- none        : academic, admin, transport issues (not handled by hostel staff)

scope rules:
- MESS            : any food, dining hall, mess timing, mess water, mess cleanliness issue
- ROOM_SHARED     : shared fixtures inside a room (ceiling fan, room tube light, room door, window, main room switchboard)
- ROOM_INDIVIDUAL : individual assigned room items (bed, mattress, study table, chair, wardrobe locker)
- COMMON_AREA     : corridor, floor washroom, geyser in common bathroom, water cooler on floor, stairs, lift, campus lawn

Examples:
- "My room light is not working" → hostel, electrical, needs_room=true, scope=ROOM_SHARED
- "My bed is broken" → hostel, maintenance, needs_room=true, scope=ROOM_INDIVIDUAL
- "Study table in room 204 is damaged" → hostel, maintenance, needs_room=true, scope=ROOM_INDIVIDUAL
- "Mess food is cold today" → mess, mess_manager, needs_room=false, scope=MESS
- "2nd floor bathroom geyser not working" → hostel, maintenance, needs_room=false, scope=COMMON_AREA
- "Corridor light is broken" → hostel, electrical, needs_room=false, scope=COMMON_AREA
- "My internal marks are wrong" → academic, none, needs_room=false, scope=COMMON_AREA"""

    try:
        resp = groq_pool.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=settings.GROQ_MODEL,
            temperature=0.0,
            max_tokens=220,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
        result = json.loads(raw)
        result["needs_room"]  = bool(result.get("needs_room", False))
        result["staff_role"]  = result.get("staff_role", "watchmen") or "watchmen"
        if result["staff_role"] == "none":
            result["staff_role"] = None
        result["scope"] = result.get("scope", "COMMON_AREA")
        if result["scope"] not in {"MESS", "ROOM_SHARED", "ROOM_INDIVIDUAL", "COMMON_AREA"}:
            result["scope"] = "COMMON_AREA"
            
        print(f"[ComplaintAgent] classify: is_complaint={result.get('is_complaint')} "
              f"category={result.get('category')} role={result.get('staff_role')} "
              f"scope={result.get('scope')} duplicate_of={result.get('duplicate_of_id')} title='{result.get('title')}'")
        return result
    except Exception as e:
        print(f"[ComplaintAgent] classify error: {e}")
        return {
            "is_complaint": False,
            "category":     "not_complaint",
            "title":        "",
            "confidence":   0.0,
            "needs_room":   False,
            "staff_role":   None,
            "scope":        "COMMON_AREA",
            "duplicate_of_id": None,
        }


# ── Stage 2: Hostel enrichment ────────────────────────────────────────────────

def enrich_hostel_details(scholar_id: str) -> dict:
    if not scholar_id:
        return {}
    chunk = doc_repo.find_hostel_allotment_chunk(scholar_id)
    if not chunk:
        return {}

    chunk_text = chunk.get("content", "")
    meta       = chunk.get("metadata", {})

    details = {"raw_chunk": chunk_text, "source_doc": meta.get("source", "")}
    for pair in chunk_text.split("|"):
        pair = pair.strip()
        if ":" in pair:
            k, v = pair.split(":", 1)
            key  = k.strip().lower().replace(" ", "_").replace(".", "")
            details[key] = v.strip()

    print(f"[ComplaintAgent] Hostel details for {scholar_id}: {list(details.keys())}")
    return details


# ── Stage 3: Similar complaint search ────────────────────────────────────────

def find_similar_complaints(complaint_text: str, complaint_title: str, scope: str, mess_id: Optional[str] = None, hostel_id: Optional[str] = None, room_number: Optional[str] = None) -> List[dict]:
    """Find similar open complaints scoped to the exact boundary."""
    try:
        # Individual room items are unique per student — no merging
        if scope == "ROOM_INDIVIDUAL":
            return []

        complaints = complaint_repo.get_open_complaints_by_scope(
            scope=scope,
            mess_id=mess_id,
            hostel_id=hostel_id,
            room_number=room_number,
            limit=20,
        )

        input_words = set(re.findall(r"\b\w{3,}\b", (complaint_text + " " + complaint_title).lower()))
        stop_words = {"the", "is", "my", "our", "was", "are", "has", "have", "not",
                      "this", "that", "for", "with", "from", "please", "and", "but"}
        input_words -= stop_words

        similar = []
        for c in complaints:
            cand_words = set(re.findall(
                r"\b\w{3,}\b",
                (c.get("title", "") + " " + c.get("description", "")).lower()
            )) - stop_words
            if not cand_words or not input_words:
                continue
            overlap = len(input_words & cand_words)
            score   = overlap / max(len(input_words | cand_words), 1)
            if score >= 0.20 or overlap >= 3:
                similar.append({
                    "id":          c["id"],
                    "title":       c["title"],
                    "vote_count":  c["vote_count"],
                    "description": (c.get("description") or "")[:100],
                    "category":    c.get("category", "general"),
                    "similarity":  round(score, 3),
                })

        return sorted(similar, key=lambda x: x["similarity"], reverse=True)[:5]

    except Exception as e:
        print(f"[ComplaintAgent] find_similar error: {e}")
        return []


# ── Orchestrator: Full complaint ingestion ────────────────────────────────────

def process_complaint(
    text: str,
    user_info: dict,
    hostel_id: Optional[str] = None,
    room_number: Optional[str] = None,
) -> dict:
    user_id    = user_info.get("id")
    scholar_id = user_info.get("scholar_id") or ""
    name       = user_info.get("name") or "Student"

    # Fetch active open tickets for semantic duplicate detection
    active_tickets = []
    if user_id:
        active_tickets = complaint_repo.get_user_active_open_tickets(user_id)

    classification = classify_complaint(text, active_tickets=active_tickets)
    if not classification.get("is_complaint"):
        return {
            "error":   "not_a_complaint",
            "message": "This message does not appear to be a complaint.",
        }

    # ── LLM Semantic Duplicate Detection Check
    dup_id = classification.get("duplicate_of_id")
    if dup_id and active_tickets:
        matched = next((t for t in active_tickets if t.get("id") == dup_id or str(t.get("id", "")).startswith(str(dup_id))), None)
        if matched:
            status_text = matched.get('status', 'in_progress').replace('_', ' ').title()
            return {
                "error": "already_open",
                "message": f"You already have an active ticket #{str(matched.get('id', ''))[:8]} for '{matched.get('title')}' (Status: {status_text}). Ground staff is already working on this.",
                "existing_complaint": matched,
            }

    category   = classification.get("category", "general")
    title      = classification.get("title") or text[:60].strip()
    staff_role = classification.get("staff_role")
    scope      = classification.get("scope", "COMMON_AREA")

    # ── Resolve Mess ID from Hostel if category is mess / scope is MESS
    mess_id: Optional[str] = None
    hostel_name = "Unknown Hostel"
    if hostel_id:
        hostel = complaint_repo.get_hostel_by_id(hostel_id)
        if hostel:
            hostel_name = hostel.get("name", hostel_name)
            mess_id = hostel.get("mess_id")

    # Scope-aware similar complaint search
    similar = find_similar_complaints(
        complaint_text=text,
        complaint_title=title,
        scope=scope,
        mess_id=mess_id,
        hostel_id=hostel_id,
        room_number=room_number,
    )
    print(f"[ComplaintAgent] Found {len(similar)} similar complaint(s) for scope={scope}")

    hostel_details: dict = {}
    if category == "hostel":
        hostel_details = enrich_hostel_details(scholar_id)

    insert_data = {
        "user_id":        user_id,
        "scholar_id":     scholar_id or None,
        "student_name":   name,
        "title":          title,
        "description":    text,
        "category":       category,
        "status":         "open",
        "staff_role":     staff_role,
        "scope":          scope,
        "mess_id":        mess_id,
        "hostel_details": hostel_details,
        "vote_count":     1,
        "hostel_id":      hostel_id or None,
        "room_number":    room_number or None,
    }

    complaint_row = complaint_repo.create_complaint(insert_data)
    complaint_id  = complaint_row.get("id")

    if complaint_id and user_id:
        complaint_repo.record_vote(complaint_id, user_id, scholar_id)

    print(f"[ComplaintAgent] Complaint saved: '{title}' [{category}/{scope}] id={complaint_id}")

    if complaint_id:
        try:
            from app.services.staff_bot import send_complaint_to_staff
            send_complaint_to_staff(
                complaint_id=complaint_id,
                title=title,
                description=text,
                category=category,
                staff_role=staff_role,
                hostel_id=hostel_id,
                hostel_name=hostel_name,
                room_number=room_number,
                student_name=name,
                scope=scope,
                mess_id=mess_id,
            )
        except Exception as fwd_err:
            print(f"[ComplaintAgent] Staff forwarding error (non-fatal): {fwd_err}")

    return {
        "complaint":      complaint_row,
        "similar":        similar,
        "hostel_details": hostel_details,
        "category":       category,
        "title":          title,
        "scope":          scope,
    }


# ── Vote on an existing complaint ─────────────────────────────────────────────

def vote_on_complaint(complaint_id: str, user_info: dict) -> dict:
    user_id    = user_info.get("id")
    scholar_id = user_info.get("scholar_id") or ""

    if complaint_repo.has_user_voted(complaint_id, user_id):
        return {"error": "already_voted", "message": "You have already voted on this complaint."}

    complaint_repo.record_vote(complaint_id, user_id, scholar_id)
    new_count = complaint_repo.increment_vote_count(complaint_id)
    print(f"[ComplaintAgent] Vote recorded on {complaint_id}: count now {new_count}")
    return {
        "message":    "Vote recorded successfully.",
        "vote_count": new_count,
    }
