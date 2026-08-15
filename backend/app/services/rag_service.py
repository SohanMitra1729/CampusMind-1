"""
app/services/rag_service.py — Hybrid Vector RAG Retrieval Engine
─────────────────────────────────────────────────────────────────
Encapsulates RAG pipeline:
  - Gemini embeddings (3072-dim)
  - Hybrid pgvector + FTS search with threshold filtering & deduplication
  - Pinned personal academic record lookup by scholar_id
  - Scope-restricted LLM answer generation via Groq
"""

import os
import httpx
from typing import Any, Dict, List, Optional
from groq import Groq

from app.core.config import settings
from app.core.logger import logger
from app.db.supabase import supabase
import app.repositories.document_repository as doc_repo

supabase_url = settings.SUPABASE_URL
supabase_key = settings.SUPABASE_SERVICE_KEY

groq_client = Groq(api_key=settings.GROQ_API_KEY or "placeholder_key")


def get_gemini_embedding(text: str) -> List[float]:
    """Call Google Gemini Embeddings API directly to fetch 1536-dim vector via httpx (sync for scripts)."""
    api_key = settings.GOOGLE_API_KEY
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:embedContent?key={api_key}"
    payload = {
        "model": "models/gemini-embedding-2",
        "content": {"parts": [{"text": text}]},
        "outputDimensionality": 1536
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post(url, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        data = response.json()
        return data["embedding"]["values"]


async def get_gemini_embedding_async(text: str) -> List[float]:
    """Call Google Gemini Embeddings API directly to fetch 1536-dim vector via httpx.AsyncClient (non-blocking)."""
    api_key = settings.GOOGLE_API_KEY
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:embedContent?key={api_key}"
    payload = {
        "model": "models/gemini-embedding-2",
        "content": {"parts": [{"text": text}]},
        "outputDimensionality": 1536
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        data = response.json()
        return data["embedding"]["values"]


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
            match_count=12,
            filter_metadata=metadata_filter
        )

        MIN_SCORE = 0.005
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

        top_chunks = unique[:6]
        print(f"[RAG] Retrieved {len(candidates)} candidates → {len(scored)} above threshold → {len(unique)} unique → {len(top_chunks)} sent to LLM")
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


PERSONAL_RESULT_KEYWORDS = [
    "my result", "my marks", "my sgpa", "my cgpa", "my grade", "my score",
    "my semester", "my performance", "my subject", "how did i", "did i pass",
    "my gpa", "my points", "my transcript", "my academic"
]


def is_personal_result_query(query: str) -> bool:
    """Detect if the query is asking about the logged-in student's own results."""
    q = query.lower()
    return any(kw in q for kw in PERSONAL_RESULT_KEYWORDS)


async def get_answer(
    query: str,
    metadata_filter: Optional[Dict[str, Any]] = None,
    user_info: Optional[Dict[str, Any]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """Run the RAG pipeline with smart retrieval and structured context."""
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
        else:
            print(f"[RAG] No personal record found for scholar_id={scholar_id}")

    context_items = await retrieve_context(query, metadata_filter)
    
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
    
    system_instruction = f"""You are CampusMind, a dedicated AI assistant exclusively for campus and institutional matters.
{personal_context}
You have access to the following institutional document excerpts to answer student queries:

{context_text}
{user_context}

════════════════════════════════════════════════
CRITICAL SCOPE RESTRICTION — READ THIS FIRST
════════════════════════════════════════════════
You ONLY answer questions that are directly related to this institution and campus life. This includes:
  • Academic results, marks, SGPA, CGPA, grades, transcripts
  • Hostel allotments, room details, hostel rules
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

Rules for campus-related responses:
1. Answer directly and conversationally — never say phrases like "based on the context", "the document says", or "according to [any source/file name]". Speak as if you already know the information. Do NOT mention any file names, document names, or source names in your answer.
2. If the user asks about their own results, marks, SGPA, CGPA, or grades — use the [STUDENT'S OWN ACADEMIC RECORD] section above (if present). That record belongs specifically to this student.
3. If the user asks about their own personal details (name, scholar ID, email), use the Active Logged-In Student info above.
4. If the question IS campus-related but the information is NOT present in the document excerpts provided, say: "I don't have that specific information right now. Please check with the administration or the relevant department."
5. For casual greetings (hi, hello, hey), respond warmly and ask how you can help with campus-related queries.
6. Keep responses clear, concise, and helpful. Use bullet points or numbered lists when listing multiple items.
"""
    
    try:
        messages = [{"role": "system", "content": system_instruction}]
        
        if chat_history:
            for msg in chat_history:
                role = "assistant" if msg["role"] == "bot" else "user"
                messages.append({"role": role, "content": msg["content"]})
                
        messages.append({"role": "user", "content": query})

        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=1024
        )
        answer = chat_completion.choices[0].message.content
    except Exception as e:
        print(f"[RAG] Generation error: {e}")
        answer = "Sorry, I encountered an error generating the response. Please try again."

    return {
        "answer": answer,
        "context": [item["content"] for item in context_items],
        "metadata": [item["metadata"] for item in context_items]
    }
