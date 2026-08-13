"""
app/services/notice_service.py — Notice & Document Business Logic
──────────────────────────────────────────────────────────────────
Orchestrates two admin workflows and the student notification endpoints:

  Workflow A — PDF Upload:
    1. Parse PDF into chunks (process_pdf)
    2. Embed chunks in rate-limit-safe batches (Gemini embeddings)
    3. Classify first excerpt (LLM via notice_agent)
    4. If notifiable doc-type: extract scholar IDs → create notice → dispatch
    5. Store chunks in documents table (pgvector RAG)

  Workflow B — Text Notice:
    1. Classify notice content (LLM)
    2. Extract scholar IDs (or broadcast)
    3. Create notice row → dispatch user_notifications
    4. Chunk + embed notice text → store in documents table

  Student CRUD:
    - get_user_notifications  (with icon enrichment)
    - mark_one_read           (ownership verified)
    - mark_all_read

Why async?
  The embed step uses asyncio.sleep() for non-blocking rate-limit backoff,
  so upload_pdf and post_text_notice must be async.
  Simple CRUD functions remain synchronous.
"""

import asyncio
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_google_genai import GoogleGenerativeAIEmbeddings

import app.repositories.notice_repository as notice_repo
import app.repositories.document_repository as doc_repo
from app.services.pdf_processor import process_pdf
from app.services.notice_agent import (
    classify_document,
    extract_scholar_ids,
    craft_notification,
    resolve_scholar_ids,
    get_all_students,
    dispatch_notifications,
    chunk_notice_text,
    NOTICE_ICONS,
    NOTIFY_TYPES,
)


# ── Gemini Embeddings (lazy singleton — initialized on first use) ──────────────
# We don't initialize at module import time so that:
#  1. Tests and other modules can import notice_service without needing GOOGLE_API_KEY
#  2. The key is read from the loaded .env at runtime, not at import time
_embeddings = None

def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
    return _embeddings

# Batching constants for rate-limit-safe embedding
_BATCH_SIZE    = 10
_SLEEP_BETWEEN = 7   # seconds between batches (asyncio — non-blocking)


# ── Private: embed with exponential backoff ────────────────────────────────────

async def _embed_with_retry(texts: List[str], max_retries: int = 5) -> List[List[float]]:
    """
    Embed a list of texts using Gemini embeddings.
    Retries up to max_retries times with exponential backoff on rate-limit errors.

    We use asyncio.sleep (non-blocking) so the FastAPI event loop is never frozen
    while we wait for the Gemini quota window to reset.
    """
    embeddings = _get_embeddings()
    for attempt in range(max_retries):
        try:
            return embeddings.embed_documents(texts)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 15 * (2 ** attempt)
                print(f"[Embed] Rate limit hit, waiting {wait}s (attempt {attempt + 1})...")
                await asyncio.sleep(wait)
            else:
                raise
    raise RuntimeError("Embedding failed after max retries.")


# ── Workflow A: PDF Upload ─────────────────────────────────────────────────────

async def upload_pdf(filename: str, file_obj) -> Dict[str, Any]:
    """
    Full PDF ingestion pipeline.

    Args:
        filename: Original filename from the UploadFile.
        file_obj: The file-like object (UploadFile.file) to read from.

    Returns:
        {
            message, content_type_detected, chunks_created,
            agent: { doc_type, notifications_sent, notification_skipped }
        }

    Raises:
        ValueError    for unsupported file type or empty PDF
        Exception     for IO / embedding / DB errors (re-raised to route)
    """
    if not filename or not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF documents are supported.")

    # ── Save to disk ────────────────────────────────────────────────────────────
    pdf_dir   = Path("../data/pdfs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    file_path = pdf_dir / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file_obj, buffer)

    # ── Parse PDF → chunks ─────────────────────────────────────────────────────
    chunks = process_pdf(str(file_path), source_name=filename)
    if not chunks:
        raise ValueError("No readable content extracted from PDF.")

    detected_type  = chunks[0]["metadata"].get("content_type", "text")
    total_uploaded = 0

    # ── Embed & store in batches ───────────────────────────────────────────────
    for i in range(0, len(chunks), _BATCH_SIZE):
        batch      = chunks[i : i + _BATCH_SIZE]
        texts      = [c["content"] for c in batch]
        embeddings = await _embed_with_retry(texts)
        rows = [
            {"content": c["content"], "metadata": c["metadata"], "embedding": emb}
            for c, emb in zip(batch, embeddings)
        ]
        doc_repo.insert_documents_batch(rows)
        total_uploaded += len(rows)
        if i + _BATCH_SIZE < len(chunks):
            await asyncio.sleep(_SLEEP_BETWEEN)

    # ── Agentic layer: classify → extract → notify (non-fatal if it fails) ─────
    agent_result: Dict[str, Any] = {"notified": 0, "doc_type": "general", "skipped": False}
    try:
        first_excerpt  = chunks[0]["content"][:300]
        classification = classify_document(first_excerpt, filename)
        doc_type       = classification.get("doc_type", "general")
        summary        = classification.get("summary", filename)
        agent_result["doc_type"] = doc_type

        print(f"[NoticeService] '{filename}' classified as: {doc_type}")

        if doc_type in NOTIFY_TYPES:
            all_texts    = [c["content"] for c in chunks]
            found_ids    = extract_scholar_ids(all_texts)
            is_broadcast = len(found_ids) == 0
            notif        = craft_notification(doc_type, summary, is_broadcast)
            users        = get_all_students() if is_broadcast else resolve_scholar_ids(found_ids)

            notice_row = notice_repo.create_notice({
                "title":          filename,
                "content":        summary,
                "notice_type":    doc_type,
                "source_type":    "pdf",
                "source_file":    filename,
                "scholar_ids":    found_ids,
                "is_broadcast":   is_broadcast,
                "notified_count": len(users),
            })
            sent = dispatch_notifications(
                notice_row["id"], users, notif["title"], notif["message_template"]
            )
            agent_result["notified"] = sent
            print(f"[NoticeService] Notifications dispatched: {sent}")
        else:
            agent_result["skipped"] = True
            print(f"[NoticeService] doc_type='{doc_type}' → no notification needed")

    except Exception as agent_err:
        # Agent failure must NOT break the main upload response
        print(f"[NoticeService] Agent pipeline error (non-fatal): {agent_err}")

    return {
        "message":               f"Successfully ingested '{filename}'!",
        "content_type_detected": detected_type,
        "chunks_created":        total_uploaded,
        "agent": {
            "doc_type":             agent_result["doc_type"],
            "notifications_sent":   agent_result["notified"],
            "notification_skipped": agent_result["skipped"],
        },
    }


# ── Admin: list & delete documents ────────────────────────────────────────────

def list_documents() -> List[Dict[str, Any]]:
    """Return all ingested document filenames and chunk counts."""
    sources = doc_repo.list_all_document_sources()
    return [{"filename": k, "chunks": v} for k, v in sources.items()]


def delete_document(filename: str) -> Dict[str, Any]:
    """
    Delete all RAG chunks for a PDF and the file on disk.
    Returns a success message dict.
    """
    doc_repo.delete_document_by_filename(filename)
    file_path = Path("../data/pdfs") / filename
    if file_path.exists():
        file_path.unlink()
    return {"message": f"Deleted document '{filename}' successfully."}


# ── Workflow B: Admin Text Notice ─────────────────────────────────────────────

async def post_text_notice(title: str, content: str) -> Dict[str, Any]:
    """
    Post a text notice, dispatch notifications, and ingest into RAG.

    Returns:
        {
            message, notice_id, notice_type, icon, is_broadcast,
            students_notified, scholar_ids_found, scholar_ids_not_found,
            rag_chunks_indexed
        }

    Raises:
        ValueError    if title or content are blank
        Exception     for LLM / DB / embedding errors (re-raised to route)
    """
    if not title.strip() or not content.strip():
        raise ValueError("Title and content are required.")

    classification = classify_document(content[:600], title)
    doc_type     = classification.get("doc_type", "student_notice")
    summary      = classification.get("summary", title)
    found_ids    = extract_scholar_ids([content])
    is_broadcast = len(found_ids) == 0
    notif        = craft_notification(doc_type, summary, is_broadcast)
    users        = get_all_students() if is_broadcast else resolve_scholar_ids(found_ids)
    not_found_ids = [sid for sid in found_ids if sid not in {u["scholar_id"] for u in users}]

    notice_row = notice_repo.create_notice({
        "title":          title,
        "content":        content,
        "notice_type":    doc_type,
        "source_type":    "text",
        "scholar_ids":    found_ids,
        "is_broadcast":   is_broadcast,
        "notified_count": len(users),
    })
    notice_id = notice_row["id"]

    sent = dispatch_notifications(notice_id, users, notif["title"], notif["message_template"])

    # Embed notice text and store in RAG documents table
    rag_chunks     = chunk_notice_text(title, content, notice_id, doc_type)
    rag_texts      = [c["content"] for c in rag_chunks]
    rag_embeddings = await _embed_with_retry(rag_texts)
    rag_rows = [
        {"content": c["content"], "metadata": c["metadata"], "embedding": emb}
        for c, emb in zip(rag_chunks, rag_embeddings)
    ]
    doc_repo.insert_documents_batch(rag_rows)

    return {
        "message":               "Notice posted and notifications dispatched.",
        "notice_id":             notice_id,
        "notice_type":           doc_type,
        "icon":                  NOTICE_ICONS.get(doc_type, "📄"),
        "is_broadcast":          is_broadcast,
        "students_notified":     sent,
        "scholar_ids_found":     found_ids,
        "scholar_ids_not_found": not_found_ids,
        "rag_chunks_indexed":    len(rag_rows),
    }


def list_notices(limit: int = 50) -> List[Dict[str, Any]]:
    """Return all notices for the admin panel (newest first)."""
    return notice_repo.get_all_notices(limit=limit)


# ── Student notification CRUD ─────────────────────────────────────────────────

def get_user_notifications(user_id: str) -> List[Dict[str, Any]]:
    """
    Fetch notifications for a student and enrich with notice_type icon.
    The icon is looked up from the parent notice row via a batched query.
    """
    notifications = notice_repo.get_user_notifications(user_id, limit=50)
    if notifications:
        notice_ids = list({n["notice_id"] for n in notifications if n["notice_id"]})
        type_map   = notice_repo.get_notice_types_by_ids(notice_ids)
        for notif in notifications:
            ntype = type_map.get(notif["notice_id"], "general")
            notif["notice_type"] = ntype
            notif["icon"]        = NOTICE_ICONS.get(ntype, "📄")
    return notifications


def mark_one_read(notif_id: str, user_id: str) -> None:
    """
    Mark a single notification as read.
    Raises PermissionError if notification not found or doesn't belong to user.
    """
    success = notice_repo.mark_notification_read(notif_id, user_id)
    if not success:
        raise PermissionError("Notification not found or access denied.")


def mark_all_read(user_id: str) -> None:
    """Mark all notifications for a user as read."""
    notice_repo.mark_all_notifications_read(user_id)
