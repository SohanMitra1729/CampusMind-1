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
    chat_id   = request.chat_id

    if not chat_id:
        title      = request.query[:50] + "..." if len(request.query) > 50 else request.query
        new_chat   = chat_repo.create_chat(user_id, title)
        chat_id    = new_chat["id"]
        chat_title = title
    else:
        existing_chat = chat_repo.get_chat_by_id_and_user(chat_id, user_id)
        if not existing_chat:
            raise HTTPException(status_code=403, detail="Chat not found or access denied.")
        chat_title = existing_chat["title"]

    # Persist user message & fetch recent history for RAG context
    chat_repo.add_message(chat_id, "user", request.query)
    chat_history = chat_repo.get_recent_history(chat_id, limit=6)

    # Run RAG pipeline
    result = get_answer(
        request.query,
        metadata_filter=request.metadata_filter,
        user_info=user_info,
        chat_history=chat_history,
    )

    # Persist bot reply
    chat_repo.add_message(chat_id, "bot", result["answer"])

    result["chat_id"] = chat_id
    result["title"]   = chat_title
    return result


@app.get("/api/chats")
async def get_chats(current_user=Depends(get_current_user)):
    """Return all chat sessions for the authenticated user."""
    return chat_repo.get_user_chats(str(current_user.id))


@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str, current_user=Depends(get_current_user)):
    success = chat_repo.delete_chat(chat_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=403, detail="Chat not found or access denied.")
    return {"message": "Chat deleted successfully."}


@app.get("/api/chats/{chat_id}/messages")
async def get_messages(chat_id: str, current_user=Depends(get_current_user)):
    user_id = str(current_user.id)
    chat = chat_repo.get_chat_by_id_and_user(chat_id, user_id)
    if not chat:
        raise HTTPException(status_code=403, detail="Chat not found or access denied.")
    return chat_repo.get_chat_messages(chat_id)


# ── Auth Endpoints ────────────────────────────────────────────────────────────────

@app.post("/api/auth/signup")
async def signup(req: SignUpRequest):
    # EmailStr already validated by Pydantic; just validate the scholar_id format
    if not re.match(r"^\d{7}$", req.scholar_id):
        raise HTTPException(status_code=400, detail="Scholar ID must be exactly 7 digits.")
    try:
        res = supabase.auth.sign_up({
            "email": req.email,
            "password": req.password,
            "options": {
                "data": {
                    "name":       req.name,
                    "username":   req.username,
                    "scholar_id": req.scholar_id,
                }
            }
        })
        if not res.user:
            raise HTTPException(status_code=400, detail="Signup failed.")
        return {"message": "Sign up successful! Please check your email for confirmation."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    email = req.identifier
    # Resolve username → email when no @ is present
    if "@" not in req.identifier:
        resolved = user_repo.get_email_by_username(req.identifier)
        if not resolved:
            raise HTTPException(status_code=400, detail="Username not found.")
        email = resolved
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": req.password})
        profile = user_repo.get_profile_by_id(res.user.id) or {}
        return {
            "session": {
                "access_token":  res.session.access_token,
                "refresh_token": res.session.refresh_token,
                "expires_at":    res.session.expires_at,
            },
            "user": {
                "id":         res.user.id,
                "email":      res.user.email,
                "name":       profile.get("name"),
                "username":   profile.get("username"),
                "scholar_id": profile.get("scholar_id"),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    email = req.identifier
    if "@" not in req.identifier:
        resolved = user_repo.get_email_by_username(req.identifier)
        if not resolved:
            raise HTTPException(status_code=400, detail="Username not found.")
        email = resolved
    try:
        FRONTEND_URL = settings.FRONTEND_URL
        supabase.auth.reset_password_for_email(email, {"redirect_to": FRONTEND_URL})
        return {"message": "Password reset email sent. Please check your inbox."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/reset-password")
async def reset_password(req: ResetPasswordRequest):
    try:
        user_response = supabase.auth.get_user(req.access_token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired reset token.")
        supabase.auth.admin.update_user_by_id(
            user_response.user.id,
            {"password": req.password},
        )
        return {"message": "Password has been reset successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Admin Document Ingestion Pipeline ─────────────────────────────────────────────
gemini_embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")


async def _embed_with_retry(texts: List[str], max_retries: int = 5) -> List[List[float]]:
    """
    Embed a batch of texts with exponential backoff on Gemini rate-limit errors.
    Uses asyncio.sleep (non-blocking) instead of time.sleep so the FastAPI event
    loop is not frozen during the wait.
    """
    for attempt in range(max_retries):
        try:
            return gemini_embeddings.embed_documents(texts)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 15 * (2 ** attempt)
                print(f"[Upload] Rate limit hit, waiting {wait}s (attempt {attempt + 1})...")
                await asyncio.sleep(wait)   # ← was blocking time.sleep()
            else:
                raise
    raise RuntimeError("Embedding failed after max retries.")


@app.post("/api/admin/upload")
async def upload_document(
    file: UploadFile = File(...),
    _admin=Depends(require_admin),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported.")

    pdf_dir   = Path("../data/pdfs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    file_path = pdf_dir / file.filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    try:
        # Smart processing: auto-detects text vs tabular PDF
        chunks = process_pdf(str(file_path), source_name=file.filename)
        if not chunks:
            raise HTTPException(status_code=400, detail="No readable content extracted from PDF.")

        # Embed & upload in rate-limit-safe batches
        BATCH_SIZE    = 10
        SLEEP_BETWEEN = 7      # seconds between batches (asyncio, non-blocking)
        total_uploaded = 0

        for i in range(0, len(chunks), BATCH_SIZE):
            batch      = chunks[i:i + BATCH_SIZE]
            texts      = [c["content"] for c in batch]
            embeddings = await _embed_with_retry(texts)
            rows = [
                {"content": c["content"], "metadata": c["metadata"], "embedding": emb}
                for c, emb in zip(batch, embeddings)
            ]
            doc_repo.insert_documents_batch(rows)
            total_uploaded += len(rows)
            if i + BATCH_SIZE < len(chunks):
                await asyncio.sleep(SLEEP_BETWEEN)

        detected_type = chunks[0]["metadata"].get("content_type", "text") if chunks else "text"

        # ── Agentic layer: classify → extract → notify ──────────────────────────
        agent_result = {"notified": 0, "doc_type": "general", "skipped": False}
        try:
            first_excerpt  = chunks[0]["content"][:300] if chunks else ""
            classification = classify_document(first_excerpt, file.filename)
            doc_type       = classification.get("doc_type", "general")
            summary        = classification.get("summary", file.filename)
            agent_result["doc_type"] = doc_type

            print(f"[Agent] '{file.filename}' classified as: {doc_type}")

            if doc_type in NOTIFY_TYPES:
                all_texts    = [c["content"] for c in chunks]
                found_ids    = extract_scholar_ids(all_texts)
                is_broadcast = len(found_ids) == 0
                notif        = craft_notification(doc_type, summary, is_broadcast)
                users        = get_all_students() if is_broadcast else resolve_scholar_ids(found_ids)

                notice_row = notice_repo.create_notice({
                    "title":          file.filename,
                    "content":        summary,
                    "notice_type":    doc_type,
                    "source_type":    "pdf",
                    "source_file":    file.filename,
                    "scholar_ids":    found_ids,
                    "is_broadcast":   is_broadcast,
                    "notified_count": len(users),
                })
                notice_id = notice_row["id"]

                sent = dispatch_notifications(
                    notice_id, users, notif["title"], notif["message_template"]
                )
                agent_result["notified"] = sent
                print(f"[Agent] Notifications dispatched: {sent}")
            else:
                agent_result["skipped"] = True
                print(f"[Agent] doc_type='{doc_type}' → no notification needed")

        except Exception as agent_err:
            # Agent failure must NOT break the main upload response
            print(f"[Agent] Pipeline error (non-fatal): {agent_err}")

        return {
            "message":               f"Successfully ingested '{file.filename}'!",
            "content_type_detected": detected_type,
            "chunks_created":        total_uploaded,
            "agent": {
                "doc_type":             agent_result["doc_type"],
                "notifications_sent":   agent_result["notified"],
                "notification_skipped": agent_result["skipped"],
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.get("/api/admin/documents")
async def list_documents(_admin=Depends(require_admin)):
    try:
        sources = doc_repo.list_all_document_sources()
        return [{"filename": k, "chunks": v} for k, v in sources.items()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/admin/documents/{filename}")
async def delete_document(filename: str, _admin=Depends(require_admin)):
    try:
        doc_repo.delete_document_by_filename(filename)
        file_path = Path("../data/pdfs") / filename
        if file_path.exists():
            file_path.unlink()
        return {"message": f"Deleted document '{filename}' successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Workflow B: Admin Text Notice ─────────────────────────────────────────────────

@app.post("/api/admin/notices")
async def post_notice(req: NoticeRequest, _admin=Depends(require_admin)):
    """Admin posts a text notice. Agent classifies, dispatches notifications,
    and ingests the notice into the RAG documents table."""
    if not req.title.strip() or not req.content.strip():
        raise HTTPException(status_code=400, detail="Title and content are required.")
    try:
        classification = classify_document(req.content[:600], req.title)
        doc_type     = classification.get("doc_type", "student_notice")
        summary      = classification.get("summary", req.title)
        found_ids    = extract_scholar_ids([req.content])
        is_broadcast = len(found_ids) == 0
        notif        = craft_notification(doc_type, summary, is_broadcast)
        users        = get_all_students() if is_broadcast else resolve_scholar_ids(found_ids)
        not_found_ids = [sid for sid in found_ids if sid not in {u["scholar_id"] for u in users}]

        notice_row = notice_repo.create_notice({
            "title":          req.title,
            "content":        req.content,
            "notice_type":    doc_type,
            "source_type":    "text",
            "scholar_ids":    found_ids,
            "is_broadcast":   is_broadcast,
            "notified_count": len(users),
        })
        notice_id = notice_row["id"]

        sent = dispatch_notifications(notice_id, users, notif["title"], notif["message_template"])

        # RAG ingestion
        rag_chunks     = chunk_notice_text(req.title, req.content, notice_id, doc_type)
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Notice pipeline failed: {str(e)}")


@app.get("/api/admin/notices-list")
async def list_notices(_admin=Depends(require_admin)):
    """Return all notices for the admin panel."""
    try:
        return notice_repo.get_all_notices(limit=50)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── User Notification Endpoints ───────────────────────────────────────────────────

@app.get("/api/notifications")
async def get_notifications(current_user=Depends(get_current_user)):
    """Fetch all notifications for the authenticated user (newest first)."""
    user_id = str(current_user.id)
    try:
        notifications = notice_repo.get_user_notifications(user_id, limit=50)
        if notifications:
            notice_ids = list({n["notice_id"] for n in notifications if n["notice_id"]})
            type_map   = notice_repo.get_notice_types_by_ids(notice_ids)
            for notif in notifications:
                ntype = type_map.get(notif["notice_id"], "general")
                notif["notice_type"] = ntype
                notif["icon"]        = NOTICE_ICONS.get(ntype, "📄")
        return notifications
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, current_user=Depends(get_current_user)):
    """Mark a single notification as read (ownership verified)."""
    user_id = str(current_user.id)
    try:
        success = notice_repo.mark_notification_read(notif_id, user_id)
        if not success:
            raise HTTPException(status_code=403, detail="Notification not found or access denied.")
        return {"message": "Notification marked as read."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/notifications/read-all")
async def mark_all_notifications_read(current_user=Depends(get_current_user)):
    """Mark all notifications as read for the authenticated user."""
    user_id = str(current_user.id)
    try:
        notice_repo.mark_all_notifications_read(user_id)
        return {"message": "All notifications marked as read."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Complaint Management Endpoints ────────────────────────────────────────────────

@app.post("/api/complaint/classify")
async def complaint_classify(
    req: ComplaintClassifyRequest,
    current_user=Depends(get_current_user_optional),
):
    """
    Fast classification-only endpoint — fire-and-forget from frontend.
    No DB writes. Returns {is_complaint, category, title, confidence} in ~300ms.
    """
    try:
        return classify_complaint(req.text)
    except Exception:
        return {"is_complaint": False, "category": "not_complaint", "title": "", "confidence": 0.0}


@app.post("/api/complaint")
async def submit_complaint(req: ComplaintRequest, current_user=Depends(get_current_user)):
    """Full complaint submission: classify → similar → hostel enrich → save."""
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Complaint text is required.")
    user_id   = str(current_user.id)
    user_info = await _fetch_profile(user_id)
    try:
        result = process_complaint(
            text=req.text,
            user_info=user_info,
            hostel_id=req.hostel_id,
            room_number=req.room_number,
        )
        if result.get("error") == "not_a_complaint":
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Complaint submission failed: {str(e)}")


@app.post("/api/complaint/{complaint_id}/vote")
async def vote_complaint(complaint_id: str, current_user=Depends(get_current_user)):
    """
    Vote on an existing complaint (upvote / 'I have the same issue').
    Records in complaint_votes for deduplication.
    """
    user_id   = str(current_user.id)
    user_info = await _fetch_profile(user_id)
    try:
        result = vote_on_complaint(complaint_id, user_info)
        if result.get("error") == "already_voted":
            raise HTTPException(status_code=409, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vote failed: {str(e)}")


@app.get("/api/my-complaints")
async def get_my_complaints(current_user=Depends(get_current_user)):
    """Return all complaints submitted by the authenticated student."""
    user_id = str(current_user.id)
    try:
        complaints = complaint_repo.get_user_complaints(user_id, limit=20)
        for c in complaints:
            cat  = c.get("category", "general")
            stat = c.get("status", "open")
            c["category_icon"] = CATEGORY_ICONS.get(cat, "📢")
            c["status_icon"]   = STATUS_LABELS.get(stat, ("🔴", "Open"))[0]
            c["status_label"]  = STATUS_LABELS.get(stat, ("🔴", "Open"))[1]
        return complaints
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
        complaints = complaint_repo.get_all_complaints(status=status, category=category, limit=limit)
        for c in complaints:
            cat  = c.get("category", "general")
            stat = c.get("status", "open")
            c["category_icon"] = CATEGORY_ICONS.get(cat, "📢")
            c["status_icon"]   = STATUS_LABELS.get(stat, ("🔴", "Open"))[0]
            c["status_label"]  = STATUS_LABELS.get(stat, ("🔴", "Open"))[1]
        return complaints
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/admin/complaints/{complaint_id}/status")
async def update_complaint_status(
    complaint_id: str,
    req: ComplaintStatusRequest,
    _admin=Depends(require_admin),
):
    """Admin action: update a complaint's status."""
    valid = {"open", "in_progress", "resolved", "dismissed"}
    if req.status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {', '.join(valid)}")
    try:
        updated = complaint_repo.update_complaint_status(complaint_id, req.status)
        if not updated:
            raise HTTPException(status_code=404, detail="Complaint not found.")
        return {"message": f"Status updated to '{req.status}'.", "complaint": updated}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Telegram Webhooks (public — called directly by Telegram servers) ──────────────

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
        return complaint_repo.get_all_hostels()
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
