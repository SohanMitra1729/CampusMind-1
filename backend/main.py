from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Any, Dict, Optional, List
import uvicorn
import asyncio
import re
import os
import shutil
from pathlib import Path

from rag import get_answer, supabase, supabase_url
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pdf_processor import process_pdf
from notice_agent import (
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
from complaint_agent import (
    classify_complaint,
    process_complaint,
    vote_on_complaint,
    CATEGORY_ICONS,
    STATUS_LABELS,
)
from telegram_bot import handle_update, setup_webhook
from staff_bot import handle_staff_update, setup_staff_webhook
from app.core.config import settings
from app.core.security import get_current_user, get_current_user_optional, require_admin

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await setup_webhook()
    await setup_staff_webhook()

# ── CORS ─────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response Schemas ────────────────────────────────────────────────────

from app.schemas.auth import (
    SignUpRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    AdminAuthRequest,
)
from app.schemas.chat import QueryRequest
from app.schemas.complaint import (
    ComplaintClassifyRequest,
    ComplaintRequest,
    ComplaintStatusRequest,
)
from app.schemas.notice import NoticeRequest
import app.repositories.chat_repository as chat_repo
import app.repositories.user_repository as user_repo
import app.repositories.complaint_repository as complaint_repo
import app.repositories.notice_repository as notice_repo
import app.repositories.document_repository as doc_repo
import app.services.auth_service as auth_service
import app.services.chat_service as chat_service
import app.services.complaint_service as complaint_service
import app.services.notice_service as notice_service


# ── Internal helper: fetch full profile by verified user_id ──────────────────────

async def _fetch_profile(user_id: str) -> Dict[str, Any]:
    """
    Fetch the profiles row for a JWT-verified user_id.
    Returns at minimum {"id": user_id} if the profile is missing.
    Never raises — callers should handle missing fields gracefully.
    """
    profile = user_repo.get_profile_by_id(user_id)
    return profile or {"id": user_id}


# ── Admin Authentication ──────────────────────────────────────────────────────────

@app.post("/api/admin/auth")
async def admin_auth(req: AdminAuthRequest):
    """
    Verify admin credentials against ADMIN_USERNAME and ADMIN_SECRET settings.
    """
    if not settings.ADMIN_USERNAME or not settings.ADMIN_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Admin credentials not configured on server.",
        )
    if req.username != settings.ADMIN_USERNAME or req.password != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin credentials.")

    return {"token": settings.ADMIN_SECRET}


# ── Chat Endpoints ────────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(request: QueryRequest, current_user=Depends(get_current_user)):
    user_id   = str(current_user.id)
    user_info = await _fetch_profile(user_id)
    try:
        return chat_service.handle_chat(
            user_id=user_id,
            user_info=user_info,
            query=request.query,
            chat_id=request.chat_id,
            metadata_filter=request.metadata_filter,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chats")
async def get_chats(current_user=Depends(get_current_user)):
    """Return all chat sessions for the authenticated user."""
    return chat_service.get_user_chats(str(current_user.id))


@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str, current_user=Depends(get_current_user)):
    success = chat_service.delete_chat(chat_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=403, detail="Chat not found or access denied.")
    return {"message": "Chat deleted successfully."}


@app.get("/api/chats/{chat_id}/messages")
async def get_messages(chat_id: str, current_user=Depends(get_current_user)):
    try:
        return chat_service.get_chat_messages(chat_id, str(current_user.id))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ── Auth Endpoints ────────────────────────────────────────────────────────────────

@app.post("/api/auth/signup")
async def signup(req: SignUpRequest):
    try:
        return auth_service.sign_up(
            email=req.email,
            password=req.password,
            name=req.name,
            username=req.username,
            scholar_id=req.scholar_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    try:
        return auth_service.login(req.identifier, req.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    try:
        return auth_service.forgot_password(req.identifier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/reset-password")
async def reset_password(req: ResetPasswordRequest):
    try:
        return auth_service.reset_password(req.access_token, req.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Admin Document Ingestion Pipeline ───────────────────────────────────────────────

@app.post("/api/admin/upload")
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


@app.get("/api/admin/documents")
async def list_documents(_admin=Depends(require_admin)):
    try:
        return notice_service.list_documents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/admin/documents/{filename}")
async def delete_document(filename: str, _admin=Depends(require_admin)):
    try:
        return notice_service.delete_document(filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Workflow B: Admin Text Notice ─────────────────────────────────────────────────

@app.post("/api/admin/notices")
async def post_notice(req: NoticeRequest, _admin=Depends(require_admin)):
    """Admin posts a text notice. Classifies, dispatches, and indexes into RAG."""
    try:
        return await notice_service.post_text_notice(req.title, req.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Notice pipeline failed: {str(e)}")


@app.get("/api/admin/notices-list")
async def list_notices(_admin=Depends(require_admin)):
    """Return all notices for the admin panel."""
    try:
        return notice_service.list_notices()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── User Notification Endpoints ────────────────────────────────────────────────────

@app.get("/api/notifications")
async def get_notifications(current_user=Depends(get_current_user)):
    """Fetch all notifications for the authenticated user (newest first)."""
    try:
        return notice_service.get_user_notifications(str(current_user.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, current_user=Depends(get_current_user)):
    """Mark a single notification as read (ownership verified)."""
    try:
        notice_service.mark_one_read(notif_id, str(current_user.id))
        return {"message": "Notification marked as read."}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/notifications/read-all")
async def mark_all_notifications_read(current_user=Depends(get_current_user)):
    """Mark all notifications as read for the authenticated user."""
    try:
        notice_service.mark_all_read(str(current_user.id))
        return {"message": "All notifications marked as read."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Complaint Management Endpoints ─────────────────────────────────────────────────────

@app.post("/api/complaint/classify")
async def complaint_classify(
    req: ComplaintClassifyRequest,
    current_user=Depends(get_current_user_optional),
):
    """Fast classification-only endpoint. No DB writes."""
    return complaint_service.classify_only(req.text)


@app.post("/api/complaint")
async def submit_complaint(req: ComplaintRequest, current_user=Depends(get_current_user)):
    """Full complaint submission: classify → similar → hostel enrich → save → forward."""
    user_id   = str(current_user.id)
    user_info = await _fetch_profile(user_id)
    try:
        return complaint_service.submit_complaint(
            text=req.text,
            user_info=user_info,
            hostel_id=req.hostel_id,
            room_number=req.room_number,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Complaint submission failed: {str(e)}")


@app.post("/api/complaint/{complaint_id}/vote")
async def vote_complaint(complaint_id: str, current_user=Depends(get_current_user)):
    """
    Upvote an existing complaint ('I have the same issue').
    Returns HTTP 409 if user already voted.
    """
    user_id   = str(current_user.id)
    user_info = await _fetch_profile(user_id)
    try:
        return complaint_service.vote(complaint_id, user_info)
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vote failed: {str(e)}")


@app.get("/api/my-complaints")
async def get_my_complaints(current_user=Depends(get_current_user)):
    """Return all complaints submitted by the authenticated student."""
    try:
        return complaint_service.get_user_complaints(str(current_user.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/complaints")
async def list_complaints(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    _admin=Depends(require_admin),
):
    """Admin endpoint: all complaints, filterable by status and category."""
    try:
        return complaint_service.get_all_complaints(status=status, category=category, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/admin/complaints/{complaint_id}/status")
async def update_complaint_status(
    complaint_id: str,
    req: ComplaintStatusRequest,
    _admin=Depends(require_admin),
):
    """Admin action: update a complaint's status."""
    try:
        return complaint_service.update_complaint_status(complaint_id, req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Telegram Webhooks (public — called directly by Telegram servers) ──────────

@app.post("/api/telegram/webhook")
async def telegram_webhook(
    background_tasks: BackgroundTasks,
    update: dict = Body(...),
):
    """Student bot webhook — returns 200 immediately; processing in background."""
    background_tasks.add_task(handle_update, update, supabase)
    return {"ok": True}


@app.get("/api/hostels")
async def list_hostels():
    """Return all hostels for the frontend dropdown (public endpoint)."""
    try:
        return complaint_service.get_hostels()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/staff/telegram/webhook")
async def staff_telegram_webhook(
    background_tasks: BackgroundTasks,
    update: dict = Body(...),
):
    """Staff bot webhook — returns 200 immediately; processing in background."""
    background_tasks.add_task(handle_staff_update, update, supabase)
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
