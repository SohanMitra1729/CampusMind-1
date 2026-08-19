"""
app/repositories/knowledge_gap_repository.py — Knowledge Gaps & Unanswered Query Insights
──────────────────────────────────────────────────────────────────────────────────────────
Stores and tracks unanswered or low-confidence student queries with smart keyword
clustering so administrators can review them, add answers, and expand pgvector memory.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import re
from app.db.supabase import supabase
from app.core.logger import logger

# In-memory storage fallback
_MEM_GAPS: List[Dict[str, Any]] = []

_STOP_WORDS = {
    "is", "are", "do", "does", "the", "a", "an", "in", "at", "for", "to", "of",
    "there", "have", "has", "how", "what", "where", "when", "can", "i", "my",
    "our", "we", "you", "u", "facility", "please", "tell", "me", "about",
    "nit", "silchar", "nitsilchar", "campus", "college", "university", "any"
}


def _extract_keywords(text: str) -> set:
    """Extract significant keywords from a query, normalizing plurals & suffixes."""
    tokens = re.findall(r"\b[a-zA-Z0-9]{3,}\b", text.lower())
    clean_tokens = set()
    for t in tokens:
        if t in _STOP_WORDS:
            continue
        # Simple suffix normalization (e.g. books -> book, booking -> book)
        if t.endswith("ing") and len(t) > 5:
            t = t[:-3]
        elif t.endswith("s") and not t.endswith("ss") and len(t) > 4:
            t = t[:-1]
        clean_tokens.add(t)
    return clean_tokens


def are_queries_similar(q1: str, q2: str) -> bool:
    """Check if two student queries are semantically asking the same question."""
    if q1.strip().lower() == q2.strip().lower():
        return True

    k1 = _extract_keywords(q1)
    k2 = _extract_keywords(q2)

    if not k1 or not k2:
        return False

    intersection = k1 & k2
    union = k1 | k2

    jaccard = len(intersection) / len(union) if union else 0.0
    containment = len(intersection) / min(len(k1), len(k2))

    return jaccard >= 0.4 or containment >= 0.75


def log_knowledge_gap(
    query: str,
    user_id: Optional[str] = None,
    confidence: float = 0.0,
    category: str = "general",
    suggested_answer: Optional[str] = None,
) -> Dict[str, Any]:
    """Log an unanswered or low-confidence query with smart duplicate clustering."""
    clean_query = query.strip()
    valid_uid = None
    if user_id:
        try:
            valid_uid = str(uuid.UUID(str(user_id)))
        except Exception:
            valid_uid = None

    # Check for existing matching questions (exact or semantic similarity)
    for existing in _MEM_GAPS:
        if existing.get("status") == "pending" and are_queries_similar(existing["query"], clean_query):
            existing["frequency"] = existing.get("frequency", 1) + 1
            existing["created_at"] = datetime.utcnow().isoformat()

            # Track alternate ways students asked this
            alt_list = existing.setdefault("alternate_queries", [])
            if clean_query.lower() != existing["query"].lower() and clean_query not in alt_list:
                alt_list.append(clean_query)

            logger.info(
                f"[KnowledgeGap] Clustered question '{clean_query}' with '{existing['query']}' (x{existing['frequency']})"
            )

            # Sync update to Supabase
            try:
                supabase.table("knowledge_gaps").update({
                    "frequency": existing["frequency"],
                    "created_at": existing["created_at"],
                }).eq("id", existing["id"]).execute()
            except Exception as e:
                # If row was not yet in Supabase, insert it now
                try:
                    supabase.table("knowledge_gaps").insert({
                        "id": existing["id"],
                        "query": existing["query"],
                        "user_id": valid_uid,
                        "confidence": existing["confidence"],
                        "category": existing["category"],
                        "suggested_answer": existing["suggested_answer"],
                        "status": "pending",
                        "frequency": existing["frequency"],
                    }).execute()
                except Exception as e2:
                    logger.debug(f"[KnowledgeGapRepo] Supabase sync note: {e2}")

            return existing

    gap_id = str(uuid.uuid4())
    gap_data = {
        "id": gap_id,
        "query": clean_query,
        "user_id": valid_uid,
        "confidence": round(float(confidence), 3),
        "category": category,
        "suggested_answer": suggested_answer or "",
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "frequency": 1,
        "alternate_queries": [],
    }

    _MEM_GAPS.insert(0, gap_data)
    logger.info(f"[KnowledgeGap] Logged new gap: '{clean_query}' (confidence: {gap_data['confidence']})")

    try:
        res = supabase.table("knowledge_gaps").insert({
            "id": gap_id,
            "query": gap_data["query"],
            "user_id": valid_uid,
            "confidence": gap_data["confidence"],
            "category": gap_data["category"],
            "suggested_answer": gap_data["suggested_answer"],
            "status": "pending",
            "frequency": gap_data["frequency"],
        }).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        logger.warning(f"[KnowledgeGapRepo] Supabase insert note: {e}")

    return gap_data


def get_all_gaps(status: str = "pending", limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch knowledge gaps for admin review with memory sync."""
    try:
        res = (
            supabase.table("knowledge_gaps")
            .select("*")
            .eq("status", status)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        if res.data and len(res.data) > 0:
            # Merge with memory cache for any local alternate_queries
            for db_row in res.data:
                for mem_row in _MEM_GAPS:
                    if db_row.get("id") == mem_row.get("id"):
                        db_row["alternate_queries"] = mem_row.get("alternate_queries", [])
            return res.data
    except Exception as e:
        logger.debug(f"[KnowledgeGapRepo] Supabase select fallback: {e}")

    return [g for g in _MEM_GAPS if g.get("status") == status][:limit]


def get_gap_by_id(gap_id: str) -> Optional[Dict[str, Any]]:
    """Fetch single knowledge gap by ID."""
    for g in _MEM_GAPS:
        if g.get("id") == gap_id:
            return g
    try:
        res = supabase.table("knowledge_gaps").select("*").eq("id", gap_id).single().execute()
        return res.data
    except Exception:
        return None


def resolve_gap(gap_id: str, status: str = "resolved") -> bool:
    """Mark a gap as resolved or dismissed."""
    for g in _MEM_GAPS:
        if g.get("id") == gap_id:
            g["status"] = status
            break
    try:
        supabase.table("knowledge_gaps").update({"status": status}).eq("id", gap_id).execute()
        return True
    except Exception:
        return True


def delete_gap(gap_id: str) -> bool:
    """Delete a knowledge gap item."""
    global _MEM_GAPS
    _MEM_GAPS = [g for g in _MEM_GAPS if g.get("id") != gap_id]
    try:
        supabase.table("knowledge_gaps").delete().eq("id", gap_id).execute()
        return True
    except Exception:
        return True
