"""
app/services/notice_agent.py — Agentic Notice Processing Pipeline
─────────────────────────────────────────────────────────────────
3-Stage funnel to classify documents and dispatch targeted notifications
with minimal LLM token usage:
  Stage 1: CLASSIFY  — LLM sees only first 300 chars + filename (~120 tokens)
  Stage 2: EXTRACT   — Pure regex, zero LLM cost
  Stage 3: CRAFT     — LLM sees only doc_type + 1-sentence summary (~80 tokens)
"""

import re
import os
import json
from typing import Optional
from app.core.key_pool import groq_pool
from app.core.config import settings
import app.repositories.user_repository as user_repo
import app.repositories.notice_repository as notice_repo

NOTIFY_TYPES = {
    "holiday",
    "exam_notice",
    "fee_notice",
    "student_notice",
    "scholarship",
    "internship",
    "event_notice",
}

NOTICE_ICONS = {
    "holiday":        "🏖️",
    "exam_notice":    "📝",
    "fee_notice":     "💰",
    "student_notice": "📢",
    "scholarship":    "🎓",
    "internship":     "💼",
    "event_notice":   "📅",
    "general":        "📄",
}


# ── Stage 1: Classify (cheap — first 300 chars only) ──────────────────────────

def classify_document(first_chunk_text: str, filename: str) -> dict:
    """Classify a document using only the first ~300 characters of its first chunk."""
    excerpt = first_chunk_text[:300].strip()

    prompt = f"""You are a document classifier for a university system.
Classify the following document excerpt and filename.

Filename: {filename}
Excerpt (first 300 characters):
\"\"\"
{excerpt}
\"\"\"

Respond with a single JSON object only (no markdown, no explanation):
{{
  "doc_type": "<one of: holiday | exam_notice | fee_notice | student_notice | scholarship | internship | event_notice | general>",
  "is_targeted": <true if the notice appears to target specific named/ID'd students, false otherwise>,
  "summary": "<one sentence describing what this document is about>"
}}

Rules:
- "holiday" = holiday list, institute holiday calendar, public holiday notice
- "exam_notice" = examination schedule, hall ticket, supplementary exam, result notice
- "fee_notice" = fee payment reminder, scholarship disbursement, fine notice
- "student_notice" = any circular/notice directed at specific students by name/ID
- "scholarship" = scholarship selection, merit list
- "internship" = internship offer, placement notice
- "event_notice" = fest, workshop, seminar, cultural event
- "general" = syllabus, notes, handbook, timetable, any non-notice academic document
- is_targeted = true ONLY when you see or expect specific registration numbers / roll numbers / names of individual students"""

    try:
        resp = groq_pool.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=settings.GROQ_MODEL,
            temperature=0.0,
            max_tokens=500,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return json.loads(raw)
    except Exception as e:
        print(f"[NoticeAgent] classify_document error: {e}")
        return {"doc_type": "general", "is_targeted": False, "summary": filename}


# ── Stage 2: Extract scholar IDs (pure regex — zero LLM cost) ─────────────────

def extract_scholar_ids(chunk_texts: list[str]) -> list[str]:
    scholar_id_pattern = re.compile(r'\b\d{7}\b')
    found: set[str] = set()
    for text in chunk_texts:
        found.update(scholar_id_pattern.findall(text))
    return sorted(found)


# ── Stage 3: Craft notification (minimal context — ~80 tokens) ────────────────

def craft_notification(doc_type: str, summary: str, is_broadcast: bool, title: str = "") -> dict:
    audience = "all students" if is_broadcast else "specific students"
    prompt = f"""You are writing a brief in-app notification for a university student portal.

Notice Title: {title or summary}
Document type: {doc_type}
Summary: {summary}
Audience: {audience}

Write a short notification for students. Respond with JSON only:
{{
  "title": "<concise notification title, max 50 chars>",
  "message_template": "<informative notification body for students, max 120 chars, use {{name}} placeholder for student name if targeted>"
}}

Rules:
- Write for STUDENTS receiving this on their campus mobile/web app.
- Do NOT say 'check admin portal' or 'admin panel'.
- Make the title and message specific to the notice topic (e.g. 'Hostel LAN Advisory', 'Power Maintenance Notice').
- Keep it friendly, clear, and actionable. No markdown."""

    try:
        resp = groq_pool.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=settings.GROQ_MODEL,
            temperature=0.3,
            max_tokens=500,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
            if parsed.get("title") and parsed.get("message_template"):
                return parsed
        if raw:
            parsed = json.loads(raw)
            if parsed.get("title") and parsed.get("message_template"):
                return parsed
    except Exception as e:
        print(f"[NoticeAgent] craft_notification error: {e}")

    # Meaningful fallback
    default_title = (title or summary or f"{doc_type.replace('_', ' ').title()} Notice")[:50]
    default_msg = (summary if summary and summary != title else f"Important update: {default_title}")[:120]
    return {
        "title": default_title,
        "message_template": default_msg,
    }


# ── Resolve scholar IDs → profile rows ───────────────────────────────────────

def resolve_scholar_ids(scholar_ids: list[str]) -> list[dict]:
    return user_repo.get_profiles_by_scholar_ids(scholar_ids)


def get_all_students() -> list[dict]:
    return user_repo.get_all_student_profiles()


# ── Dispatch: insert user_notifications rows ─────────────────────────────────

def dispatch_notifications(
    notice_id: str,
    users: list[dict],
    title: str,
    message_template: str,
    doc_type: str = "general"
) -> int:
    if not users:
        return 0

    rows = []
    for user in users:
        name = user.get("name") or "Student"
        message = message_template.replace("{name}", name)
        rows.append({
            "notice_id":            notice_id,
            "user_id":              user["id"],
            "scholar_id":           user.get("scholar_id"),
            "notification_title":   title,
            "notification_message": message,
            "is_read":              False,
        })

    try:
        notice_repo.create_user_notifications_batch(rows, batch_size=50)
        print(f"[NoticeAgent] Dispatched {len(rows)} notifications for notice {notice_id}")
        
        try:
            from app.services.telegram_bot import send_telegram_push
            if settings.TELEGRAM_BOT_TOKEN:
                user_ids = [u["id"] for u in users]
                tg_profiles = user_repo.get_telegram_enabled_profiles(user_ids)

                icon = NOTICE_ICONS.get(doc_type, "📢")
                for p in tg_profiles:
                    name = p.get("name", "Student")
                    msg  = message_template.replace("{name}", name)
                    send_telegram_push(p["telegram_chat_id"], title, msg, icon)
                print(f"[NoticeAgent] Telegram push sent to {len(tg_profiles)} users")
        except Exception as e:
            print(f"[NoticeAgent] Telegram push error (non-fatal): {e}")

        return len(rows)
    except Exception as e:
        print(f"[NoticeAgent] dispatch_notifications error: {e}")
        return 0


# ── Text-notice chunker (for Workflow B RAG ingestion) ───────────────────────

def chunk_notice_text(
    title: str,
    content: str,
    notice_id: str,
    notice_type: str,
    is_broadcast: bool = True
) -> list[dict]:
    MAX_CHARS = 800
    full_text = f"{title}\n\n{content}"
    safe_filename = f"{title[:40].strip()} (Notice).txt"
    chunks = []
    for i in range(0, len(full_text), MAX_CHARS):
        chunk_text = full_text[i : i + MAX_CHARS]
        chunks.append({
            "content": chunk_text,
            "metadata": {
                "source": f"notice_{notice_id}",
                "filename": safe_filename,
                "notice_id": notice_id,
                "notice_type": notice_type,
                "title": title,
                "category": notice_type,
                "content_type": "text",
                "department": "Campus Administration",
                "audience": "All Students" if is_broadcast else "Targeted Scholars",
            },
        })
    return chunks
