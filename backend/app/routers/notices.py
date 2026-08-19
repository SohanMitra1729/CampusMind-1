"""
app/routers/notices.py — Document Ingestion, Notices & Notification Routes
────────────────────────────────────────────────────────────────────────────
Handles:
  POST   /api/admin/upload
  GET    /api/admin/documents
  DELETE /api/admin/documents/{filename}
  POST   /api/admin/notices
  GET    /api/admin/notices-list
  GET    /api/notifications
  PATCH  /api/notifications/read-all
  PATCH  /api/notifications/{notif_id}/read
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Depends

from app.core.security import get_current_user, require_admin
from app.core.logger import logger
from app.core.exceptions import (
    ValidationException,
    ForbiddenException,
    NotFoundException,
    InternalServerErrorException,
)
from app.schemas.notice import NoticeRequest
import app.services.notice_service as notice_service

router = APIRouter()


# ── Admin: document ingestion ──────────────────────────────────────────────────

@router.post("/api/admin/upload")
async def upload_document(
    file: UploadFile = File(...),
    _admin=Depends(require_admin),
):
    try:
        return await notice_service.upload_pdf(file.filename, file.file)
    except ValueError as e:
        raise ValidationException(str(e))
    except Exception as e:
        logger.exception(f"[Notices] Ingestion failed for {file.filename}: {e}")
        raise InternalServerErrorException("Document ingestion failed. Please try again.")


@router.get("/api/admin/documents")
async def list_documents(_admin=Depends(require_admin)):
    try:
        return notice_service.list_documents()
    except Exception as e:
        logger.exception(f"[Notices] list_documents error: {e}")
        raise InternalServerErrorException("Failed to load documents list.")


from fastapi.responses import FileResponse, Response
from app.db.supabase import supabase

PDF_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "pdfs"


@router.get("/api/documents/{filename}/view")
async def view_pdf_document(filename: str):
    """
    Serve a PDF document for inline viewing in a browser tab.
      1. Checks local disk cache (fast for local development).
      2. If not found on local disk (e.g. on Render with ephemeral disk),
         streams directly from Supabase Cloud Storage.
    """
    # 1. Fetch from Supabase Cloud Storage (Primary source of truth for Render & Cloud)
    try:
        pdf_bytes = supabase.storage.from_("campus-documents").download(filename)
        if pdf_bytes:
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename=\"{filename}\"",
                    "Cache-Control": "public, max-age=86400",
                },
            )
    except Exception as e:
        logger.warning(f"[Notices] Supabase storage download error for '{filename}': {e}")

    # 2. Check local cache fallback
    file_path = PDF_DIR / filename
    if not file_path.exists():
        alt_path = Path("data/pdfs") / filename
        if alt_path.exists():
            file_path = alt_path

    if file_path.exists():
        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=\"{filename}\"",
                "Cache-Control": "public, max-age=86400",
            },
        )

    raise NotFoundException(f"Document '{filename}' not found.")


@router.delete("/api/admin/documents/{filename}")
async def delete_document(filename: str, _admin=Depends(require_admin)):
    try:
        return notice_service.delete_document(filename)
    except Exception as e:
        logger.exception(f"[Notices] delete_document error for {filename}: {e}")
        raise InternalServerErrorException("Failed to delete document.")


# ── Admin: text notices ────────────────────────────────────────────────────────

@router.post("/api/admin/notices")
async def post_notice(req: NoticeRequest, _admin=Depends(require_admin)):
    """Admin posts a text notice. Classifies, dispatches, and indexes into RAG."""
    try:
        return await notice_service.post_text_notice(req.title, req.content)
    except ValueError as e:
        raise ValidationException(str(e))
    except Exception as e:
        logger.exception(f"[Notices] Notice broadcast failed: {e}")
        raise InternalServerErrorException("Notice pipeline failed. Please try again.")


@router.get("/api/admin/notices-list")
async def list_notices(_admin=Depends(require_admin)):
    """Return all notices for the admin panel."""
    try:
        return notice_service.list_notices()
    except Exception as e:
        logger.exception(f"[Notices] list_notices error: {e}")
        raise InternalServerErrorException("Failed to load notices list.")


@router.delete("/api/admin/notices/{notice_id}")
async def delete_notice(notice_id: str, _admin=Depends(require_admin)):
    """Delete a broadcast notice, its user notifications, and its pgvector chunks."""
    try:
        return notice_service.delete_notice(notice_id)
    except Exception as e:
        logger.exception(f"[Notices] delete_notice error for {notice_id}: {e}")
        raise InternalServerErrorException("Failed to delete notice.")


# ── Student: notifications ─────────────────────────────────────────────────────

@router.get("/api/notifications")
async def get_notifications(current_user=Depends(get_current_user)):
    """Fetch all notifications for the authenticated user (newest first)."""
    try:
        return notice_service.get_user_notifications(str(current_user.id))
    except Exception as e:
        logger.exception(f"[Notices] get_notifications error: {e}")
        raise InternalServerErrorException("Failed to fetch notifications.")


# NOTE: /read-all MUST be registered before /{notif_id}/read.
# FastAPI matches routes top-down; if /{notif_id}/read came first,
# a request to /read-all would match it with notif_id="read-all".

@router.patch("/api/notifications/read-all")
async def mark_all_notifications_read(current_user=Depends(get_current_user)):
    """Mark all notifications as read for the authenticated user."""
    try:
        notice_service.mark_all_read(str(current_user.id))
        return {"message": "All notifications marked as read."}
    except Exception as e:
        logger.exception(f"[Notices] mark_all_notifications_read error: {e}")
        raise InternalServerErrorException("Failed to update notifications.")


@router.patch("/api/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, current_user=Depends(get_current_user)):
    """Mark a single notification as read (ownership verified)."""
    try:
        notice_service.mark_one_read(notif_id, str(current_user.id))
        return {"message": "Notification marked as read."}
    except PermissionError as e:
        raise ForbiddenException(str(e))
    except Exception as e:
        logger.exception(f"[Notices] mark_notification_read error for {notif_id}: {e}")
        raise InternalServerErrorException("Failed to mark notification as read.")


# ── Admin: Knowledge Gaps & Learned FAQs ───────────────────────────────────────

import app.repositories.knowledge_gap_repository as gap_repo
from pydantic import BaseModel

class ApproveGapRequest(BaseModel):
    answer: str
    question: Optional[str] = None

@router.get("/api/admin/knowledge-gaps")
async def list_knowledge_gaps(status: str = "pending", _admin=Depends(require_admin)):
    """Return all unanswered or trending student questions for admin review."""
    try:
        return gap_repo.get_all_gaps(status=status)
    except Exception as e:
        logger.exception(f"[Notices] list_knowledge_gaps error: {e}")
        raise InternalServerErrorException("Failed to fetch knowledge gaps.")


@router.post("/api/admin/knowledge-gaps/{gap_id}/approve")
async def approve_knowledge_gap(
    gap_id: str,
    req: ApproveGapRequest,
    _admin=Depends(require_admin),
):
    """Admin approves/answers a knowledge gap. Automatically ingests it into RAG vector memory."""
    try:
        gap = gap_repo.get_gap_by_id(gap_id)
        question = req.question or (gap.get("query") if gap else "FAQ")
        title = f"FAQ: {question[:60]}"
        content = f"Question: {question}\n\nAnswer: {req.answer}"

        # Ingest directly into RAG as an official notice / FAQ chunk
        await notice_service.post_text_notice(title, content)
        gap_repo.resolve_gap(gap_id, "resolved")
        return {"message": "FAQ successfully answered and ingested into knowledge base."}
    except Exception as e:
        logger.exception(f"[Notices] approve_knowledge_gap error: {e}")
        raise InternalServerErrorException("Failed to ingest FAQ into knowledge base.")


@router.delete("/api/admin/knowledge-gaps/{gap_id}")
async def dismiss_knowledge_gap(gap_id: str, _admin=Depends(require_admin)):
    """Dismiss a knowledge gap without ingesting it."""
    try:
        gap_repo.delete_gap(gap_id)
        return {"message": "Knowledge gap dismissed."}
    except Exception as e:
        logger.exception(f"[Notices] dismiss_knowledge_gap error: {e}")
        raise InternalServerErrorException("Failed to dismiss knowledge gap.")

