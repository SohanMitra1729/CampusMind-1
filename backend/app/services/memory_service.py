"""
app/services/memory_service.py — Student Profile Memory & Conversation Compression
───────────────────────────────────────────────────────────────────────────────────
Handles:
  1. Extracting and storing persistent student profile memory across chats
     (academic curriculum, residential status, career targets, campus roles, scholarships).
  2. Compressing long multi-turn conversations into token-efficient rolling summaries.
  3. Tracking knowledge gaps and unanswered queries for admin FAQ ingestion.
"""

import re
import json
from typing import Any, Dict, List, Optional, Tuple
from app.core.logger import logger
from app.core.key_pool import groq_pool
import app.repositories.user_repository as user_repo
import app.repositories.knowledge_gap_repository as gap_repo

# Rolling summary cache by chat_id
_CHAT_SUMMARIES: Dict[str, str] = {}

# ── Extraction Patterns (0-cost, fast regex heuristics) ─────────────────────────

_PROGRAM_PATTERN = re.compile(r"\b(b\.?tech|m\.?tech|mca|ph\.?d|b\.?arch|m\.?sc|dual degree)\b", re.IGNORECASE)
_DEPT_PATTERN = re.compile(
    r"\b(computer science|cse|electronics & communication|electronics|ece|mechanical|civil|electrical|ee|eie|instrumentation|chemical)\b",
    re.IGNORECASE,
)
_YEAR_PATTERN = re.compile(
    r"\b(1st year|2nd year|3rd year|4th year|first year|second year|third year|fourth year|freshman|sophomore|junior|senior|\d(?:st|nd|rd|th) sem(?:ester)?)\b",
    re.IGNORECASE,
)
_SECTION_PATTERN = re.compile(r"\b(section\s*[a-d]|sec\s*[a-d]|group\s*g?[1-8]|batch\s*b?[1-8])\b", re.IGNORECASE)
_RESIDENT_PATTERN = re.compile(r"\b(day scholar|dayscholar|commuter|local student|hosteler|hosteller|boarder)\b", re.IGNORECASE)
_HOSTEL_PATTERN = re.compile(
    r"\b(bh[-\s]?[1-9]|gh[-\s]?[1-3]|aryabhatta|ramanujan|pg hostel|girls hostel|boys hostel)\b",
    re.IGNORECASE,
)
_ROOM_PATTERN = re.compile(r"\b(room\s*(?:no\.?|number)?\s*[:#-]?\s*(\d{2,4}[a-z]?))\b", re.IGNORECASE)
_CAREER_PATTERN = re.compile(
    r"\b(software engineering|sde|web dev|ai/ml|machine learning|data science|core electronics|vlsi|embedded|gate|cat|gre|upsc|placements|internship)\b",
    re.IGNORECASE,
)
_ROLE_PATTERN = re.compile(
    r"\b(class representative|cr|mess secretary|hostel prefect|placement coordinator|club lead|general secretary)\b",
    re.IGNORECASE,
)
_CLUB_PATTERN = re.compile(
    r"\b(coding club|robotics club|gymkhana|nss|ncc|e-cell|entrepreneurship club|literary club|music club|dance club|gdsc)\b",
    re.IGNORECASE,
)
_SCHOLARSHIP_PATTERN = re.compile(
    r"\b(nsp scholarship|national scholarship|tuition fee waiver|tfw|post matric|post-matric|dasa|reliance scholarship)\b",
    re.IGNORECASE,
)


def extract_and_save_user_facts(user_id: str, query: str):
    """
    Lightweight rule-based + heuristic extractor for personal student facts.
    Runs asynchronously with 0ms added streaming latency.
    """
    if not user_id or not query:
        return

    q_lower = query.lower()
    extracted: Dict[str, Any] = {}

    # 1. Program / Degree
    prog_match = _PROGRAM_PATTERN.search(q_lower)
    if prog_match and ("i am" in q_lower or "student" in q_lower or "pursuing" in q_lower or "doing" in q_lower):
        extracted["program"] = prog_match.group(1).upper().replace(".", "")

    # 2. Department / Branch
    dept_match = _DEPT_PATTERN.search(q_lower)
    if dept_match and ("i am in" in q_lower or "my branch" in q_lower or "i study" in q_lower or "from" in q_lower or "dept" in q_lower):
        extracted["department"] = dept_match.group(1).upper()

    # 3. Year / Semester
    year_match = _YEAR_PATTERN.search(q_lower)
    if year_match and ("i am in" in q_lower or "my year" in q_lower or "student" in q_lower or "sem" in q_lower):
        extracted["academic_year"] = year_match.group(1).title()

    # 4. Section / Lab Group
    sec_match = _SECTION_PATTERN.search(q_lower)
    if sec_match:
        extracted["section_or_group"] = sec_match.group(1).title()

    # 5. Resident Status (Day Scholar vs Hosteler)
    res_match = _RESIDENT_PATTERN.search(q_lower)
    if res_match:
        val = res_match.group(1).lower()
        extracted["resident_type"] = "Day Scholar" if ("day" in val or "commuter" in val or "local" in val) else "Hosteler"

    # 6. Hostel & Room
    hostel_match = _HOSTEL_PATTERN.search(q_lower)
    if hostel_match and ("i live in" in q_lower or "my hostel" in q_lower or "stay in" in q_lower or "hostel" in q_lower):
        extracted["hostel"] = hostel_match.group(1).upper()
        extracted["resident_type"] = "Hosteler"

    room_match = _ROOM_PATTERN.search(q_lower)
    if room_match:
        extracted["room_number"] = room_match.group(2).upper()
        extracted["resident_type"] = "Hosteler"

    # 7. Dietary Preference
    if "veg" in q_lower and ("mess" in q_lower or "diet" in q_lower or "food" in q_lower):
        if "non-veg" in q_lower or "non veg" in q_lower:
            extracted["dietary_preference"] = "Non-Vegetarian"
        else:
            extracted["dietary_preference"] = "Vegetarian"

    # 8. Career Goal / Target Focus
    career_match = _CAREER_PATTERN.search(q_lower)
    if career_match and ("target" in q_lower or "preparing for" in q_lower or "interested in" in q_lower or "aiming" in q_lower or "career" in q_lower):
        extracted["career_focus"] = career_match.group(1).title()

    # 9. Campus Leadership Role
    role_match = _ROLE_PATTERN.search(q_lower)
    if role_match and ("i am the" in q_lower or "i am a" in q_lower or "as a" in q_lower or "cr" in q_lower):
        extracted["campus_role"] = role_match.group(1).title()

    # 10. Club Memberships
    club_match = _CLUB_PATTERN.search(q_lower)
    if club_match and ("member" in q_lower or "joined" in q_lower or "part of" in q_lower or "in" in q_lower):
        extracted["club_membership"] = club_match.group(1).title()

    # 11. Scholarship / Fee Category
    schol_match = _SCHOLARSHIP_PATTERN.search(q_lower)
    if schol_match and ("scholarship" in q_lower or "fee" in q_lower or "category" in q_lower or "under" in q_lower):
        extracted["financial_category"] = schol_match.group(1).title()

    if extracted:
        logger.info(f"[MemoryService] Extracted student facts for {user_id}: {extracted}")
        user_repo.update_user_memories(user_id, extracted)


def get_student_memory_context(user_id: Optional[str]) -> str:
    """Format persistent student memory facts for injection into RAG prompt."""
    if not user_id:
        return ""
    memories = user_repo.get_user_memories(user_id)
    if not memories:
        return ""

    lines = [
        "[PERSISTENT STUDENT PROFILE MEMORY — Learned Across Conversations]:",
        "The active student has previously established the following context. Tailor answers accordingly without asking again:",
    ]
    for k, v in memories.items():
        label = k.replace("_", " ").title()
        lines.append(f"• {label}: {v}")

    return "\n" + "\n".join(lines) + "\n"


def get_compressed_chat_history(
    chat_id: str,
    raw_history: List[Dict[str, str]],
) -> Tuple[str, List[Dict[str, str]]]:
    """
    Compresses older conversation turns into a rolling summary if history > 6 turns.
    Maintains bounded input token budget for 100% free-tier operation.
    """
    if not raw_history or len(raw_history) <= 6:
        return ("", raw_history)

    # Keep the latest 4 messages raw
    older_messages = raw_history[:-4]
    recent_messages = raw_history[-4:]

    # Check if we can summarize the older turns
    older_text = "\n".join(
        f"{'Student' if m.get('role') == 'user' else 'CampusMind'}: {m.get('content', '')[:120]}"
        for m in older_messages
    )

    summary = _CHAT_SUMMARIES.get(chat_id, "")

    # Re-summarize if older turns grew significantly
    if not summary or len(older_messages) > 4:
        try:
            client = groq_pool.get_client()
            prompt = (
                f"Condense this earlier campus chat dialogue into a short 1-2 sentence context summary:\n\n"
                f"{older_text}\n\n"
                f"Summary:"
            )
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
                temperature=0.3,
            )
            summary = resp.choices[0].message.content.strip()
            _CHAT_SUMMARIES[chat_id] = summary
        except Exception as e:
            logger.warning(f"[MemoryService] Summarization fallback: {e}")
            summary = "Student previously discussed campus inquiries and academic matters."
            _CHAT_SUMMARIES[chat_id] = summary

    summary_context = f"[PREVIOUS CONVERSATION CONTEXT]:\n{summary}\n" if summary else ""
    return (summary_context, recent_messages)


def record_unanswered_query(
    query: str,
    user_id: Optional[str] = None,
    confidence: float = 0.0,
    category: str = "general",
):
    """Logs knowledge gaps so admins can review and vectorize answers."""
    # Filter out casual greetings
    casual = {"hi", "hello", "hey", "thanks", "thank you", "bye", "ok", "cool"}
    if query.strip().lower() in casual:
        return
    gap_repo.log_knowledge_gap(
        query=query,
        user_id=user_id,
        confidence=confidence,
        category=category,
    )
