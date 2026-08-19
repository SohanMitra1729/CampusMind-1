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


def list_all_document_sources() -> List[Dict[str, Any]]:
    """
    Fetch all document metadata using pagination (handling > 1000 rows in Supabase),
    group chunks by document, and return a list of enriched document objects.
    """
    all_rows: List[Dict[str, Any]] = []
    page_size = 1000
    start = 0

    while True:
        res = (
            supabase.table("documents")
            .select("metadata")
            .range(start, start + page_size - 1)
            .execute()
        )
        data = res.data or []
        if not data:
            break
        all_rows.extend(data)
        if len(data) < page_size:
            break
        start += page_size

    docs: Dict[str, Dict[str, Any]] = {}
    for row in all_rows:
        meta = row.get("metadata") or {}
        fn = meta.get("filename") or meta.get("source")
        if not fn:
            continue
        
        filename = fn.split("/")[-1].split("\\")[-1]
        if filename not in docs:
            docs[filename] = {
                "filename": filename,
                "title": meta.get("title") or filename.replace(".pdf", ""),
                "content_type": meta.get("content_type", "pdf"),
                "category": meta.get("category", "general"),
                "department": meta.get("department", "All Departments"),
                "audience": meta.get("audience", "All Students"),
                "description": meta.get("description", ""),
                "chunks": 0,
            }
        docs[filename]["chunks"] += 1

    return sorted(list(docs.values()), key=lambda x: x["filename"].lower())


def delete_document_by_filename(filename: str):
    """Delete all chunks matching a specific source PDF filename using JSONB arrow operators."""
    clean = filename.strip()
    base = clean.replace(".pdf", "").strip()
    for field in ["filename", "source", "file_name", "title", "source_file"]:
        try:
            supabase.table("documents").delete().eq(f"metadata->>{field}", clean).execute()
        except Exception as e:
            print(f"[DocumentRepo] delete by metadata->>{field} error: {e}")
        if base != clean:
            try:
                supabase.table("documents").delete().eq(f"metadata->>{field}", base).execute()
            except Exception:
                pass


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

