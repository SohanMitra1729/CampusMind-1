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
  PATCH  /api/notifications/{notif_id}/read
  PATCH  /api/notifications/read-all
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends

from app.core.security import get_current_user, require_admin
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/api/admin/documents")
async def list_documents(_admin=Depends(require_admin)):
    try:
        return notice_service.list_documents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/admin/documents/{filename}")
async def delete_document(filename: str, _admin=Depends(require_admin)):
    try:
        return notice_service.delete_document(filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Admin: text notices ────────────────────────────────────────────────────────

@router.post("/api/admin/notices")
async def post_notice(req: NoticeRequest, _admin=Depends(require_admin)):
    """Admin posts a text notice. Classifies, dispatches, and indexes into RAG."""
    try:
        return await notice_service.post_text_notice(req.title, req.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Notice pipeline failed: {str(e)}")


@router.get("/api/admin/notices-list")
async def list_notices(_admin=Depends(require_admin)):
    """Return all notices for the admin panel."""
    try:
        return notice_service.list_notices()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Student: notifications ─────────────────────────────────────────────────────

@router.get("/api/notifications")
async def get_notifications(current_user=Depends(get_current_user)):
    """Fetch all notifications for the authenticated user (newest first)."""
    try:
        return notice_service.get_user_notifications(str(current_user.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/api/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, current_user=Depends(get_current_user)):
    """Mark a single notification as read (ownership verified)."""
    try:
        notice_service.mark_one_read(notif_id, str(current_user.id))
        return {"message": "Notification marked as read."}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
