"""
app/repositories/document_repository.py — Documents & Vectors Data Access Layer
─────────────────────────────────────────────────────────────────────────────
Encapsulates all Supabase database queries for pgvector documents and PDF metadata.
"""

from typing import Any, Dict, List, Optional
from app.db.supabase import supabase


def insert_documents_batch(rows: List[Dict[str, Any]]):
    """Insert a batch of embedded document chunks into the documents table."""
    if not rows:
        return
    supabase.table("documents").insert(rows).execute()


def list_all_document_sources() -> Dict[str, int]:
    """
    Fetch all document metadata, count chunk frequencies grouped by filename,
    and return a dictionary of { filename: chunk_count }.
    """
    res = supabase.table("documents").select("metadata").execute()
    docs: Dict[str, int] = {}
    for row in (res.data or []):
        meta = row.get("metadata") or {}
        src = meta.get("source")
        if src:
            filename = src.split("/")[-1].split("\\")[-1]
            docs[filename] = docs.get(filename, 0) + 1
    return dict(sorted(docs.items()))


def delete_document_by_filename(filename: str):
    """Delete all chunks matching a specific source PDF filename."""
    supabase.table("documents").delete().like("metadata->source", f"%{filename}").execute()


def find_hostel_allotment_chunk(scholar_id: str) -> Optional[Dict[str, Any]]:
    """
    Query the documents table for a student's hostel allotment chunk
    (by metadata->>regn_no or content search).
    """
    if not scholar_id:
        return None
    try:
        res = (
            supabase.table("documents")
            .select("content, metadata")
            .eq("metadata->>regn_no", scholar_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            # Fallback to looser search
            res = (
                supabase.table("documents")
                .select("content, metadata")
                .like("content", f"%{scholar_id}%")
                .in_("metadata->>content_type", ["tabular", "ocr_tabular"])
                .limit(1)
                .execute()
            )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[DocumentRepo] find_hostel_allotment_chunk error: {e}")
        return None


def execute_hybrid_search(
    query_text: str,
    query_embedding: List[float],
    match_count: int = 6,
    filter_metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Execute the RPC call to the pgvector hybrid_search stored procedure."""
    rpc_params = {
        "query_text":      query_text,
        "query_embedding": query_embedding,
        "match_count":     match_count,
        "filter":          filter_metadata or {},
    }
    res = supabase.rpc("hybrid_search", rpc_params).execute()
    return res.data or []

