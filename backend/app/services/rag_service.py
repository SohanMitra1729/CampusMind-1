"""
app/services/rag_service.py — Hybrid Vector RAG Retrieval Engine
─────────────────────────────────────────────────────────────────
Encapsulates RAG pipeline:
  - Gemini embeddings (1536-dim)
  - Hybrid pgvector + FTS search with threshold filtering & deduplication
  - Ground-truth campus hostels & facilities directory from Supabase
  - Pinned personal academic record lookup by scholar_id
  - Scope-restricted LLM answer generation via Groq
"""

import os
import httpx
from typing import Any, Dict, List, Optional
from groq import Groq, AsyncGroq

from app.core.config import settings
from app.core.logger import logger
from app.core.key_pool import gemini_pool, groq_pool
from app.db.supabase import supabase
import app.repositories.document_repository as doc_repo
import app.repositories.complaint_repository as complaint_repo
import app.repositories.notice_repository as notice_repo
import app.services.memory_service as memory_service

supabase_url = settings.SUPABASE_URL
supabase_key = settings.SUPABASE_SERVICE_KEY


def get_gemini_embedding(text: str) -> List[float]:
    """Fetch 1536-dim vector using automatic Gemini multi-key failover pool."""
    return gemini_pool.get_embedding(text)


async def get_gemini_embedding_async(text: str) -> List[float]:
    """Fetch 1536-dim vector asynchronously using automatic Gemini multi-key failover pool."""
    return await gemini_pool.get_embedding_async(text)


def hybrid_search(
    query_text: str,
    query_embedding: List[float],
    match_count: int = 6,
    filter_metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search (vector similarity + full-text search) via Supabase RPC.
    Calls PostgreSQL function: hybrid_search_documents
    """
    try:
        return doc_repo.execute_hybrid_search(
            query_text=query_text,
            query_embedding=query_embedding,
            match_count=match_count,
            filter_metadata=filter_metadata,
        )
    except Exception as e:
        logger.error(f"[RAG] hybrid_search error: {e}")
        return []


async def retrieve_context(query: str, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Query Supabase hybrid_search, then filter by score and deduplicate."""
    try:
        query_embedding = await get_gemini_embedding_async(query)
        candidates = hybrid_search(
            query_text=query,
            query_embedding=query_embedding,
            match_count=8,
            filter_metadata=metadata_filter
        )

        MIN_SCORE = 0.018
        scored = [c for c in candidates if (c.get("similarity") or 0) >= MIN_SCORE]

        seen_fingerprints: list[str] = []
        unique: list[Dict[str, Any]] = []
        for chunk in scored:
            fingerprint = chunk["content"][:200].strip()
            is_duplicate = any(
                len(set(fingerprint) & set(fp)) / max(len(set(fingerprint)), len(set(fp)), 1) > 0.85
                for fp in seen_fingerprints
            )
            if not is_duplicate:
                seen_fingerprints.append(fingerprint)
                unique.append(chunk)

        top_chunks = unique[:4]
        logger.info(f"[RAG] Retrieved {len(candidates)} candidates -> {len(scored)} above threshold -> {len(unique)} unique -> {len(top_chunks)} sent to LLM")
        return top_chunks

    except Exception as e:
        print(f"[RAG] Retrieval error: {e}")
        return []


def fetch_personal_record(scholar_id: str) -> Optional[Dict[str, Any]]:
    """Directly fetch a student's own result record by registration number (scholar_id)."""
    try:
        res = supabase.table("documents") \
            .select("content, metadata") \
            .eq("metadata->>regn_no", scholar_id) \
            .limit(1) \
            .execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        print(f"[RAG] Personal record lookup error: {e}")
    return None


def fetch_campus_hostels_context() -> str:
    """Fetch the authoritative campus hostels and mess directory from public.hostels DB."""
    try:
        hostels = complaint_repo.get_all_hostels()
        if not hostels:
            return ""
        lines = [
            "[OFFICIAL CAMPUS HOSTELS & MESS DIRECTORY — Ground-Truth Institutional Data]:",
            "Use this authoritative list whenever students ask about hostel availability, boys/girls hostels, room sharing, batch years, or messes:",
        ]
        for h in hostels:
            gender = (h.get("gender") or "Campus").capitalize()
            batch  = h.get("target_years") or "All Batches"
            desc   = h.get("sharing_description") or ""
            mess   = h.get("mess_name") or "Hostel Mess"
            lines.append(f"• {h.get('name')} [{gender} | Batch: {batch} | Rooms: {desc} | Assigned Mess: {mess}]")
        return "\n" + "\n".join(lines) + "\n"
    except Exception as e:
        logger.warning(f"[RAG] fetch_campus_hostels_context error: {e}")
        return ""


def fetch_recent_notices_context() -> str:
    """Fetch the latest institutional notices broadcasted by administration."""
    try:
        notices = notice_repo.get_all_notices(limit=6)
        if not notices:
            return ""
        lines = [
            "[LATEST OFFICIAL CAMPUS NOTICES & BROADCASTS — Ground-Truth Admin Announcements]:",
            "Use this authoritative list whenever students ask about recent notices, announcements, circulars, or updates:",
        ]
        for n in notices:
            title = n.get("title") or "Notice"
            content = n.get("content") or ""
            ntype = (n.get("notice_type") or "general").replace("_", " ").title()
            date = str(n.get("created_at", ""))[:10]
            lines.append(f"• [{ntype}] {title} (Date: {date}): {content[:350]}")
        return "\n" + "\n".join(lines) + "\n"
    except Exception as e:
        logger.warning(f"[RAG] fetch_recent_notices_context error: {e}")
        return ""


PERSONAL_RESULT_KEYWORDS = [
    "my result", "my marks", "my sgpa", "my cgpa", "my grade", "my score",
    "my semester", "my performance", "my subject", "how did i", "did i pass",
    "my gpa", "my points", "my transcript", "my academic"
]


def is_personal_result_query(query: str) -> bool:
    """Detect if the query is asking about the logged-in student's own results."""
    q = query.lower()
    return any(kw in q for kw in PERSONAL_RESULT_KEYWORDS)


def _build_system_instruction(
    personal_context: str,
    context_text: str,
    user_context: str,
    hostels_context: str,
    notices_context: str = "",
    student_memory: str = "",
    summary_context: str = "",
) -> str:
    return f"""You are CampusMind, a dedicated AI assistant exclusively for campus and institutional matters at this university.
{personal_context}
{student_memory}
{hostels_context}
{notices_context}
{summary_context}
You have access to the following institutional document excerpts:

{context_text}
{user_context}

════════════════════════════════════════════════
CRITICAL SCOPE RESTRICTION — READ THIS FIRST
════════════════════════════════════════════════
You ONLY answer questions that are directly related to this institution and campus life. This includes:
  • Academic results, marks, SGPA, CGPA, grades, transcripts
  • Hostel directory, room sharing, hostel allotments, mess assignments
  • Notices, circulars, announcements, and events
  • Internships and placement opportunities listed by the college
  • Fee details, scholarship information
  • Campus facilities, departments, timetables
  • Complaints and grievances related to campus services
  • Student profile details (name, scholar ID, email)
  • Any other information found in the institutional documents provided

If a question is NOT related to this institution or campus life — including but not limited to:
  general knowledge, science, history, geography, mathematics, coding help,
  writing essays or poems, news, entertainment, sports, recipes, travel,
  or any topic unrelated to campus affairs —
you MUST respond with EXACTLY this message and nothing else:
"I'm CampusMind, your campus assistant! I can only help with questions related to our institution — such as results, hostel details, notices, internships, complaints, and campus information. For general questions, please use a general-purpose AI assistant. 😊"

Do NOT attempt to answer general questions even if you know the answer from your training data.
════════════════════════════════════════════════

CRITICAL ANTI-HALLUCINATION & STRICT GROUNDING RULES:
1. STRICT GROUNDING: You MUST base all factual campus answers, office hours, contact steps, and facility details strictly on the provided institutional document excerpts or official directories.
2. DIRECTORY LIMITATION: Contact Directories (such as 'NITS Administration Directory' or 'Faculty Directory') contain ONLY staff names and phone numbers. They DO NOT provide procedural guidelines. NEVER use contact directories to make speculative guesses about processes, room bookings, or facilities (e.g., Guest House booking, Medical Record Book MRB, swimming pool rules, dispensary).
3. NEVER INVENT PROCEDURES: If the document excerpts do NOT explicitly state the official process (e.g. how to book the campus guest house, how to collect Medical Record Book MRB, swimming pool facilities), DO NOT fabricate steps, fake hours (e.g., '8 AM to 6 PM'), or conversational guesses.
4. NEVER OFFER IMPOSSIBLE ACTIONS: Never offer to perform offline administrative actions on behalf of the user (e.g. do NOT say 'I will forward your request to the hostel office/dispensary' or 'I can help draft an email').
5. UNKNOWN CAMPUS INFORMATION: If the question IS campus-related but the specific facts or step-by-step procedures are NOT in the excerpts or official hostel list, you MUST strictly respond with:
   "I don't have that specific information right now. Please check with the administration or the relevant department."

General response rules:
1. Answer directly and conversationally — never say phrases like "based on the context", "the document says", or "according to [any source/file name]". Speak as if you already know the information. Do NOT mention any file names, document names, or source names in your answer.
2. If the user asks about hostel availability, boys hostels, girls hostels, room sharing, or messes — USE the [OFFICIAL CAMPUS HOSTELS & MESS DIRECTORY] above. It contains the complete, accurate ground-truth list.
3. If the user asks about their own results, marks, SGPA, CGPA, or grades — use the [STUDENT'S OWN ACADEMIC RECORD] section above (if present). That record belongs specifically to this student.
4. If the user asks about their own personal details (name, scholar ID, email), use the Active Logged-In Student info above.
5. If the user asks HOW to submit, file, or give a complaint, or report an issue — ALWAYS inform them warmly that they can submit it RIGHT HERE with you in this chat! Invite them to describe their issue (e.g., "My room fan is broken", "Corridor light not working", "Mess food issue") and tell them you will file it for them immediately. NEVER tell them to use an external website, grievance cell, or offline form.
6. For casual greetings (hi, hello, hey), respond warmly and ask how you can help with campus-related queries.
7. Tables & Markdown: Whenever formatting structured lists or tabular data (like marks, course grades, SGPA/CGPA, or hostel lists), format them as a valid Markdown Table with clear newlines between each row.
"""


def _is_unanswered_fallback(text: str) -> bool:
    """Detect if the generated response is a fallback/missing-info response (handles Unicode apostrophes)."""
    if not text:
        return False
    normalized = text.lower().replace("’", "'").replace("‘", "'").replace("`", "'")
    fallback_phrases = [
        "don't have that specific information",
        "don't have official information",
        "don't have information",
        "do not have that specific information",
        "do not have official information",
        "do not have information",
        "check with the administration",
        "campus assistant! i can only help",
        "not available in my knowledge base",
        "no specific information right now",
    ]
    return any(p in normalized for p in fallback_phrases)


async def get_answer(
    query: str,
    metadata_filter: Optional[Dict[str, Any]] = None,
    user_info: Optional[Dict[str, Any]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    chat_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the RAG pipeline with smart retrieval and structured context."""
    user_id = user_info.get("id") or user_info.get("user_id") if user_info else None
    scholar_id = user_info.get("scholar_id") if user_info else None
    personal_context = ""

    if scholar_id and is_personal_result_query(query):
        record = fetch_personal_record(scholar_id)
        if record:
            personal_context = (
                f"\n\n[STUDENT'S OWN ACADEMIC RECORD — Directly retrieved by Registration Number]\n"
                f"{record['content']}\n"
            )
            print(f"[RAG] Personal record found for scholar_id={scholar_id}")

    context_items = await retrieve_context(query, metadata_filter)
    hostels_context = fetch_campus_hostels_context()
    notices_context = fetch_recent_notices_context()
    student_memory = memory_service.get_student_memory_context(user_id)
    summary_context, final_history = memory_service.get_compressed_chat_history(
        chat_id or "default",
        chat_history or [],
    )

    max_score = max((item.get("similarity") or 0) for item in context_items) if context_items else 0.0

    if context_items:
        context_parts = []
        for item in context_items:
            source = item.get("metadata", {}).get("source", "unknown")
            source_name = source.split("/")[-1].split("\\")[-1]
            context_parts.append(f"[Source: {source_name}]\n{item['content'].strip()}")
        context_text = "\n\n---\n\n".join(context_parts)
    else:
        context_text = "(No relevant documents found for this query.)"

    user_context = ""
    if user_info:
        user_context = (
            f"\nActive Logged-In Student:\n"
            f"- Name: {user_info.get('name')}\n"
            f"- Scholar ID: {user_info.get('scholar_id')}\n"
            f"- Email: {user_info.get('email')}\n"
            f"- Username: {user_info.get('username')}\n"
        )
    
    system_instruction = _build_system_instruction(
        personal_context=personal_context,
        context_text=context_text,
        user_context=user_context,
        hostels_context=hostels_context,
        notices_context=notices_context,
        student_memory=student_memory,
        summary_context=summary_context,
    )
    
    try:
        messages = [{"role": "system", "content": system_instruction}]
        
        if final_history:
            for msg in final_history:
                role = "assistant" if msg["role"] == "bot" else "user"
                messages.append({"role": role, "content": msg["content"]})
                
        messages.append({"role": "user", "content": query})

        chat_completion = groq_pool.chat_completion(
            messages=messages,
            model=settings.GROQ_MODEL,
            temperature=0.2,
            max_tokens=1024
        )
        answer = chat_completion.choices[0].message.content
        if _is_unanswered_fallback(answer) or (max_score < 0.025 and not personal_context):
            memory_service.record_unanswered_query(query, user_id=user_id, confidence=max_score)
            filtered_metadata = []
        else:
            filtered_metadata = [
                item["metadata"] for item in context_items if (item.get("similarity") or 0) >= 0.025
            ]

    except Exception as e:
        print(f"[RAG] Generation error: {e}")
        answer = "Sorry, I encountered an error generating the response. Please try again."
        filtered_metadata = []

    return {
        "answer": answer,
        "context": [item["content"] for item in context_items],
        "metadata": filtered_metadata,
    }


async def get_answer_stream(
    query: str,
    metadata_filter: Optional[Dict[str, Any]] = None,
    user_info: Optional[Dict[str, Any]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    chat_id: Optional[str] = None,
):
    """
    Async generator version of get_answer.
    Yields SSE lines: 'data: {"token": "..."}\n\n'
    Finishes with:   'data: {"done": true, "sources": [...]}\n\n'
    """
    import json as _json

    user_id = user_info.get("id") or user_info.get("user_id") if user_info else None
    scholar_id = user_info.get("scholar_id") if user_info else None
    personal_context = ""

    if scholar_id and is_personal_result_query(query):
        record = fetch_personal_record(scholar_id)
        if record:
            personal_context = (
                f"\n\n[STUDENT'S OWN ACADEMIC RECORD — Directly retrieved by Registration Number]\n"
                f"{record['content']}\n"
            )

    context_items = await retrieve_context(query, metadata_filter)
    hostels_context = fetch_campus_hostels_context()
    notices_context = fetch_recent_notices_context()
    student_memory = memory_service.get_student_memory_context(user_id)
    summary_context, final_history = memory_service.get_compressed_chat_history(
        chat_id or "default",
        chat_history or [],
    )

    max_score = max((item.get("similarity") or 0) for item in context_items) if context_items else 0.0

    if context_items:
        context_parts = []
        for item in context_items:
            source = item.get("metadata", {}).get("source", "unknown")
            source_name = source.split("/")[-1].split("\\")[-1]
            context_parts.append(f"[Source: {source_name}]\n{item['content'].strip()}")
        context_text = "\n\n---\n\n".join(context_parts)
    else:
        context_text = "(No relevant documents found for this query.)"

    user_context = ""
    if user_info:
        user_context = (
            f"\nActive Logged-In Student:\n"
            f"- Name: {user_info.get('name')}\n"
            f"- Scholar ID: {user_info.get('scholar_id')}\n"
            f"- Email: {user_info.get('email')}\n"
            f"- Username: {user_info.get('username')}\n"
        )

    system_instruction = _build_system_instruction(
        personal_context=personal_context,
        context_text=context_text,
        user_context=user_context,
        hostels_context=hostels_context,
        notices_context=notices_context,
        student_memory=student_memory,
        summary_context=summary_context,
    )

    messages = [{"role": "system", "content": system_instruction}]
    if final_history:
        for msg in final_history:
            role = "assistant" if msg["role"] == "bot" else "user"
            messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": query})

    # Only include sources that have actual relevance score
    sources = [
        item.get("metadata", {}) for item in context_items if (item.get("similarity") or 0) >= 0.025
    ]
    accumulated_answer = []

    try:
        async for chunk in groq_pool.async_chat_completion_stream(
            messages=messages,
            model=settings.GROQ_MODEL,
            temperature=0.2,
            max_tokens=1024,
        ):
            token = chunk.choices[0].delta.content or ""
            if token:
                accumulated_answer.append(token)
                yield f"data: {_json.dumps({'token': token})}\n\n"
        
        full_text = "".join(accumulated_answer)
        if _is_unanswered_fallback(full_text) or (max_score < 0.025 and not personal_context):
            memory_service.record_unanswered_query(query, user_id=user_id, confidence=max_score)
        
        if _is_unanswered_fallback(full_text):
            sources = []  # Clear sources when answer is a fallback or out of scope

    except Exception as e:
        logger.error(f"[RAG] Streaming generation error: {e}")
        sources = []
        yield f"data: {_json.dumps({'token': 'Sorry, I encountered an error. Please try again.'})}\n\n"

    # Final event with metadata
    yield f"data: {_json.dumps({'done': True, 'sources': sources})}\n\n"
