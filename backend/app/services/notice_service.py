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
from typing import Any, Dict, List, Optional, BinaryIO

from app.db.supabase import supabase
from app.core.key_pool import gemini_pool
import app.repositories.notice_repository as notice_repo
import app.repositories.document_repository as doc_repo
from app.core.logger import logger
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


# Batching constants for rate-limit-safe embedding
_BATCH_SIZE    = 10
_SLEEP_BETWEEN = 2   # seconds between batches (asyncio — non-blocking)
BUCKET_NAME = "campus-documents"


def _ensure_storage_bucket() -> None:
    try:
        supabase.storage.create_bucket(
            BUCKET_NAME,
            options={"public": True, "file_size_limit": 52428800} # 50MB
        )
    except Exception:
        pass


# ── Private: embed with automatic key rotation & backoff ───────────────────────

async def _embed_with_retry(texts: List[str], max_retries: int = 5) -> List[List[float]]:
    """
    Embed a list of texts using Gemini embeddings via the automatic multi-key failover pool.
    """
    results: List[List[float]] = []
    for text in texts:
        emb = await gemini_pool.get_embedding_async(text)
        results.append(emb)
    return results


# ── Workflow A: PDF Upload & Ingestion ────────────────────────────────────────

async def upload_pdf(filename: str, file_obj: BinaryIO) -> Dict[str, Any]:
    """
    Ingest an uploaded PDF document:
      1. Upload to Supabase Storage (permanent global CDN, safe for Render ephemeral disk)
      2. Parse text & tables via PyPDF / pdfplumber
      3. Generate Gemini vector embeddings
      4. Batch insert into Supabase pgvector
      5. Classify document type & extract scholar IDs
      6. Dispatch targeted student notifications
    """
    if not filename or not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF documents are supported.")

    file_bytes = file_obj.read()

    # ── Upload to Supabase Cloud Storage (Permanent CDN) ──────────────────────
    _ensure_storage_bucket()
    try:
        supabase.storage.from_(BUCKET_NAME).upload(
            path=filename,
            file=file_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )
        logger.info(f"[NoticeService] Uploaded '{filename}' to Supabase Storage bucket '{BUCKET_NAME}'.")
    except Exception as storage_err:
        logger.warning(f"[NoticeService] Initial storage upload warning: {storage_err}")
        # Verify if file was saved or exists in storage
        try:
            download_check = supabase.storage.from_(BUCKET_NAME).download(filename)
            if not download_check:
                raise storage_err
        except Exception:
            logger.error(f"[NoticeService] Failed to persist '{filename}' to Supabase Storage: {storage_err}")
            raise RuntimeError(f"Could not save '{filename}' to Supabase Cloud Storage. Please check storage bucket permissions.")

    # ── Save temporary file for parsing ───────────────────────────────────────
    pdf_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    file_path = pdf_dir / filename

    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    # ── Parse PDF → chunks & Embed with Transactional Rollback ───────────────
    import gc
    try:
        chunks = process_pdf(str(file_path), source_name=filename)
        if not chunks:
            raise ValueError("No readable content extracted from PDF.")

        detected_type  = chunks[0]["metadata"].get("content_type", "text")
        total_uploaded = 0

        # Clear old chunks for this file (handles re-upload / updates)
        doc_repo.delete_document_by_filename(filename)
        logger.info(f"[NoticeService] Cleared existing chunks for '{filename}' before re-ingestion.")

        # Embed & store in rate-limit-safe, memory-safe batches
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
            gc.collect()
            if i + _BATCH_SIZE < len(chunks):
                await asyncio.sleep(_SLEEP_BETWEEN)

    except Exception as process_err:
        logger.error(f"[NoticeService] Ingestion failed for '{filename}', performing rollback: {process_err}")
        # Rollback: Clean up any partial chunks from pgvector and storage
        doc_repo.delete_document_by_filename(filename)
        try:
            supabase.storage.from_(BUCKET_NAME).remove([filename])
        except Exception:
            pass
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass
        raise process_err

    # ── Agentic layer: classify → extract → notify (non-fatal if it fails) ─────
    agent_result: Dict[str, Any] = {"notified": 0, "doc_type": "general", "skipped": False}
    try:
        first_excerpt  = chunks[0]["content"][:300]
        classification = classify_document(first_excerpt, filename)
        doc_type       = classification.get("doc_type", "general")
        summary        = classification.get("summary", filename)
        agent_result["doc_type"] = doc_type

        logger.info(f"[NoticeService] '{filename}' classified as: {doc_type}")

        if doc_type in NOTIFY_TYPES:
            all_texts    = [c["content"] for c in chunks]
            found_ids    = extract_scholar_ids(all_texts)
            is_broadcast = len(found_ids) == 0
            clean_title  = filename.replace(".pdf", "").replace("_", " ").strip()
            notif_msg    = summary if summary and summary != filename else f"New {doc_type.replace('_', ' ')}: {clean_title}"
            users        = get_all_students() if is_broadcast else resolve_scholar_ids(found_ids)

            notice_row = notice_repo.create_notice({
                "title":          clean_title,
                "content":        summary,
                "notice_type":    doc_type,
                "source_type":    "pdf",
                "source_file":    filename,
                "scholar_ids":    found_ids,
                "is_broadcast":   is_broadcast,
                "notified_count": len(users),
            })
            sent = dispatch_notifications(
                notice_row["id"], users, clean_title, notif_msg, doc_type=doc_type
            )
            agent_result["notified"] = sent
            agent_result["notifications_sent"] = sent
            agent_result["is_broadcast"] = is_broadcast
            agent_result["skipped"] = False
            agent_result["notification_skipped"] = False
            logger.info(f"[NoticeService] Notifications dispatched: {sent}")
        else:
            agent_result["skipped"] = True
            agent_result["notification_skipped"] = True
            logger.info(f"[NoticeService] doc_type='{doc_type}' → no notification needed")

    except Exception as agent_err:
        # Agent failure must NOT break the main upload response
        logger.error(f"[NoticeService] Agent pipeline error (non-fatal): {agent_err}")

    # Note: File is kept on disk in data/pdfs for student/admin viewing and download

    return {
        "message":               f"Successfully ingested '{filename}'!",
        "content_type_detected": detected_type,
        "chunks_created":        total_uploaded,
        "agent":                 agent_result,
    }


# ── Admin: list & delete documents ────────────────────────────────────────────

def list_documents() -> List[Dict[str, Any]]:
    """Return all ingested documents with rich metadata and chunk counts."""
    return doc_repo.list_all_document_sources()


def delete_document(filename: str) -> Dict[str, Any]:
    """
    Completely cascade-delete an ingested document across the entire system:
      1. Delete all RAG vector chunks from pgvector (documents table)
      2. Find all parent notices in notices table matching this filename / title
      3. For each matching notice, delete all student notifications (user_notifications table)
      4. Delete matching notice rows from notices table
      5. Remove the physical PDF from Supabase Storage CDN (campus-documents bucket)
      6. Remove the PDF from local cache on disk (data/pdfs)
    """
    clean_name = filename.strip()
    base_name = clean_name.replace(".pdf", "").strip()

    # 1. Delete all RAG chunks from documents table
    try:
        doc_repo.delete_document_by_filename(clean_name)
    except Exception as e:
        logger.warning(f"[NoticeService] Error deleting chunks for '{clean_name}': {e}")

    # 2. Find and delete all corresponding notices and user_notifications
    try:
        res1 = supabase.table("notices").select("id").eq("source_file", clean_name).execute()
        res2 = supabase.table("notices").select("id").eq("title", clean_name).execute()
        res3 = supabase.table("notices").select("id").eq("title", base_name).execute()

        notice_ids = list({
            n["id"] for res in [res1, res2, res3] for n in (res.data or []) if n.get("id")
        })

        if notice_ids:
            # Delete user notifications
            supabase.table("user_notifications").delete().in_("notice_id", notice_ids).execute()
            # Delete RAG chunks tied by notice_id
            for nid in notice_ids:
                try:
                    supabase.table("documents").delete().eq("metadata->>notice_id", nid).execute()
                    supabase.table("documents").delete().eq("metadata->>source_id", nid).execute()
                except Exception:
                    pass
            # Delete notices
            supabase.table("notices").delete().in_("id", notice_ids).execute()
            logger.info(f"[NoticeService] Cascade deleted {len(notice_ids)} notices & user notifications for '{clean_name}'.")
    except Exception as e:
        logger.warning(f"[NoticeService] Error deleting notices/notifications for '{clean_name}': {e}")

    # Fallback: Also clean up any user_notifications matching filename or title
    try:
        supabase.table("user_notifications").delete().ilike("notification_title", f"%{base_name}%").execute()
    except Exception:
        pass

    # 3. Remove from Supabase Storage CDN
    try:
        supabase.storage.from_(BUCKET_NAME).remove([clean_name])
        logger.info(f"[NoticeService] Removed '{clean_name}' from Supabase Storage.")
    except Exception as err:
        logger.warning(f"[NoticeService] Could not remove '{clean_name}' from Supabase Storage: {err}")

    # 4. Remove from local cache
    for base_path in [
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "pdfs",
        Path.cwd() / "data" / "pdfs",
        Path.cwd().parent / "data" / "pdfs",
    ]:
        file_path = base_path / clean_name
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"[NoticeService] Deleted local PDF file '{file_path}'.")
            except Exception as unlink_err:
                logger.warning(f"[NoticeService] Could not unlink local PDF '{file_path}': {unlink_err}")

    return {"message": f"Deleted document '{filename}' and all associated notifications successfully."}


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

    classification = classify_document(content[:300], title)
    doc_type      = classification.get("doc_type", "student_notice")
    summary       = classification.get("summary", title)
    found_ids     = extract_scholar_ids([content])
    is_broadcast  = len(found_ids) == 0
    notif_msg     = summary if summary and summary != title else content[:120].strip()
    users         = get_all_students() if is_broadcast else resolve_scholar_ids(found_ids)
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

    sent = dispatch_notifications(notice_id, users, title, notif_msg, doc_type=doc_type)

    # Embed notice text and store in RAG documents table
    rag_chunks     = chunk_notice_text(title, content, notice_id, doc_type, is_broadcast=is_broadcast)
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


def delete_notice(notice_id: str) -> Dict[str, Any]:
    """Delete a notice, its dispatched user notifications, and its pgvector chunks."""
    success = notice_repo.delete_notice_by_id(notice_id)
    if not success:
        raise RuntimeError("Failed to delete notice from database.")
    return {"message": "Notice deleted successfully.", "notice_id": notice_id}


# ── Student notification CRUD ─────────────────────────────────────────────────

def get_user_notifications(user_id: str) -> List[Dict[str, Any]]:
    """
    Fetch notifications for a student and enrich with notice_type icon,
    source_type ('pdf' vs 'text'), source_file, notice_title, and notice_content for direct viewing.
    """
    notifications = notice_repo.get_user_notifications(user_id, limit=50)
    if notifications:
        notice_ids = list({n["notice_id"] for n in notifications if n.get("notice_id")})
        notice_map = notice_repo.get_notice_types_by_ids(notice_ids)
        for notif in notifications:
            parent = notice_map.get(notif.get("notice_id")) or {}
            ntype = parent.get("notice_type", "general")
            notif["notice_type"]    = ntype
            notif["source_type"]    = parent.get("source_type", "text")
            notif["source_file"]    = parent.get("source_file")
            notif["notice_title"]   = parent.get("title") or notif.get("notification_title")
            notif["notice_content"] = parent.get("content")
            notif["is_broadcast"]   = parent.get("is_broadcast", True)
            notif["icon"]           = NOTICE_ICONS.get(ntype, "📄")
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
