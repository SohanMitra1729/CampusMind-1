"""
complaint_agent.py — Agentic Complaint Management Pipeline
──────────────────────────────────────────────────────────
3-stage funnel:

  Stage 1: CLASSIFY  — LLM determines if input is a complaint (~60 tokens, Groq)
  Stage 2: ENRICH    — If hostel-related, fetch room/hostel from RAG chunks (DB only)
  Stage 3: SIMILAR   — keyword-overlap search for similar open complaints (DB only)

Design goal: Stage 1 runs on /api/complaint/classify (fire-and-forget from frontend).
             Stages 2-3 run on /api/complaint only when user explicitly submits.
             /api/chat is NEVER touched.
"""

import re
import os
import json
from typing import Optional, List, Dict, Any

from groq import Groq
from app.core.config import settings

groq_client = Groq(api_key=settings.GROQ_API_KEY or "placeholder_key")

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

def classify_complaint(text: str) -> dict:
    """
    Determine if the input text is a complaint or grievance.
    Single Groq call — must stay fast (<300ms).

    Returns:
        {
            "is_complaint": bool,
            "category":     str,    # hostel|academic|admin|facility|mess|transport|general|not_complaint
            "title":        str,    # short complaint title (empty if not a complaint)
            "confidence":   float,
            "needs_room":   bool,   # True if complaint is specific to a single room
            "staff_role":   str,    # electrical|cleaning|mess_manager|watchmen (who should handle it)
        }
    """
    excerpt = text[:400].strip()
    prompt = f"""You are a complaint classifier for a university student portal.

Student message:
\"\"\"{excerpt}\"\"\"

Respond with a single JSON object only (no markdown):
{{
  "is_complaint": <true if this is a complaint/grievance/problem, false if it is a general question>,
  "category": "<hostel|academic|admin|facility|mess|transport|general|not_complaint>",
  "title": "<short complaint title max 60 chars, empty string if not a complaint>",
  "confidence": <0.0-1.0>,
  "needs_room": <true if the complaint is clearly about a specific room (e.g. "my room", "room 204", "my bathroom"), false if it affects the whole hostel/building/mess/campus>,
  "staff_role": "<which staff role should handle this: electrical | cleaning | mess_manager | watchmen | none>"
}}

staff_role selection rules (pick the BEST match based on the actual problem, not just the category):
- electrical  : lights, fans, power, switches, sockets, electrical fittings, wiring, inverter, generator
- cleaning    : garbage, cleanliness, dirty bathroom, waste, sweeping, mopping, sanitation, cockroaches, pest
- mess_manager: food quality, meal timing, mess hygiene, canteen, water in mess, dining
- watchmen    : security, entry/exit, gate, theft, outsiders, curfew, general hostel safety
- none        : academic, admin, transport issues (not handled by hostel staff)

needs_room rules:
- true  : "my room", "my fan", "my bathroom", "room 204" — affects one specific room
- false : "entire hostel", "block", "common area", "mess", "campus", "WiFi" — affects multiple people

Examples:
- "My room light is not working" → hostel, electrical, needs_room=true
- "Light in the corridor is broken" → hostel, electrical, needs_room=false
- "Mess food has insects" → mess, mess_manager, needs_room=false
- "Garbage not collected in my room" → hostel, cleaning, needs_room=true
- "Common bathroom is very dirty" → hostel, cleaning, needs_room=false
- "Stranger entered the hostel" → hostel, watchmen, needs_room=false
- "My internal marks are wrong" → academic, none, needs_room=false"""

    try:
        resp = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            max_tokens=150,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
        result = json.loads(raw)
        # Ensure boolean/string fields are always present and correct type
        result["needs_room"]  = bool(result.get("needs_room", False))
        result["staff_role"]  = result.get("staff_role", "watchmen") or "watchmen"
        if result["staff_role"] == "none":
            result["staff_role"] = None
        print(f"[ComplaintAgent] classify: is_complaint={result.get('is_complaint')} "
              f"category={result.get('category')} staff_role={result.get('staff_role')} "
              f"needs_room={result.get('needs_room')} confidence={result.get('confidence')}")
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
        }


import app.repositories.document_repository as doc_repo


# ── Stage 2: Hostel enrichment ────────────────────────────────────────────────

def enrich_hostel_details(scholar_id: str) -> dict:
    """
    Query the RAG documents table for the student's hostel allotment chunk.
    Works because hostel allotment PDFs are ingested with metadata.regn_no set.

    Returns a dict of parsed hostel details, or {} if not found.
    """
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


import app.repositories.complaint_repository as complaint_repo


# ── Stage 3: Similar complaint search ────────────────────────────────────────

def find_similar_complaints(complaint_text: str, complaint_title: str, category: str) -> List[dict]:
    """
    Find existing open complaints similar to the new one.
    Uses keyword overlap on title + same category filter.
    Returns list of {id, title, vote_count, description, similarity}.
    """
    try:
        complaints = complaint_repo.get_open_complaints_for_similarity(limit=30)

        # Word-overlap similarity between new complaint and existing titles+descriptions
        input_words = set(re.findall(r"\b\w{3,}\b", (complaint_text + " " + complaint_title).lower()))
        # Remove common stop words
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
            if score >= 0.15 or overlap >= 3:
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
    """
    Full agentic complaint pipeline:
      1. Classify  (LLM — fast)
      2. Similar   (DB keyword search)
      3. Enrich    (DB hostel lookup — only if hostel category)
      4. Save      (Supabase insert)
      5. Forward   (staff_bot — route to matching staff)
    """
    user_id    = user_info.get("id")
    scholar_id = user_info.get("scholar_id") or ""
    name       = user_info.get("name") or "Student"

    # ── Stage 1: Classify ──────────────────────────────────────────────────────
    classification = classify_complaint(text)
    if not classification.get("is_complaint"):
        return {
            "error":   "not_a_complaint",
            "message": "This message does not appear to be a complaint.",
        }

    category   = classification.get("category", "general")
    title      = classification.get("title") or text[:60].strip()
    staff_role = classification.get("staff_role")  # LLM-determined, e.g. "electrical"

    # ── Stage 2: Similar complaints ────────────────────────────────────────────
    similar = find_similar_complaints(text, title, category)
    print(f"[ComplaintAgent] Found {len(similar)} similar complaint(s)")

    # ── Stage 3: Hostel enrichment ─────────────────────────────────────────────
    hostel_details: dict = {}
    if category == "hostel":
        hostel_details = enrich_hostel_details(scholar_id)

    # ── Stage 4: Persist complaint ─────────────────────────────────────────────
    insert_data = {
        "user_id":        user_id,
        "scholar_id":     scholar_id or None,
        "student_name":   name,
        "title":          title,
        "description":    text,
        "category":       category,
        "status":         "open",
        "hostel_details": hostel_details,
        "vote_count":     1,
        "hostel_id":      hostel_id or None,
        "room_number":    room_number or None,
    }

    complaint_row = complaint_repo.create_complaint(insert_data)
    complaint_id  = complaint_row.get("id")

    # Record that this user is the first "voter" on their own complaint
    if complaint_id and user_id:
        complaint_repo.record_vote(complaint_id, user_id, scholar_id)

    print(f"[ComplaintAgent] Complaint saved: '{title}' [{category}] id={complaint_id}")

    # ── Stage 5: Forward to staff via staff_bot ───────────────────────────────
    if complaint_id:
        try:
            from staff_bot import send_complaint_to_staff
            # Look up hostel name if hostel_id supplied
            hostel_name = "Unknown Hostel"
            if hostel_id:
                hostel = complaint_repo.get_hostel_by_id(hostel_id)
                if hostel:
                    hostel_name = hostel.get("name", hostel_name)
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
            )
        except Exception as fwd_err:
            print(f"[ComplaintAgent] Staff forwarding error (non-fatal): {fwd_err}")

    return {
        "complaint":      complaint_row,
        "similar":        similar,
        "hostel_details": hostel_details,
        "category":       category,
        "title":          title,
    }


# ── Vote on an existing complaint ─────────────────────────────────────────────

def vote_on_complaint(complaint_id: str, user_info: dict) -> dict:
    """
    Record that a student agrees with / has the same issue as an existing complaint.
    Increments vote_count atomically.
    Returns updated complaint or raises if vote already cast.
    """
    user_id    = user_info.get("id")
    scholar_id = user_info.get("scholar_id") or ""

    if complaint_repo.has_user_voted(complaint_id, user_id):
        return {"error": "already_voted", "message": "You have already voted on this complaint."}

    # Insert vote record
    complaint_repo.record_vote(complaint_id, user_id, scholar_id)

    # Increment vote_count
    new_count = complaint_repo.increment_vote_count(complaint_id)
    print(f"[ComplaintAgent] Vote recorded on {complaint_id}: count now {new_count}")
    return {
        "message":    "Vote recorded successfully.",
        "vote_count": new_count,
    }
