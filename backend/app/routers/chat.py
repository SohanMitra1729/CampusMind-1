"""
app/routers/chat.py — Chat & RAG Routes
────────────────────────────────────────
Handles:
  POST   /api/chat/stream  (SSE streaming — primary)
  POST   /api/chat         (JSON fallback)
  GET    /api/chats
  DELETE /api/chats/{chat_id}
  GET    /api/chats/{chat_id}/messages
"""

import json
from typing import Any, Dict, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.core.security import get_current_user
from app.core.deps import fetch_profile
from app.schemas.chat import QueryRequest
import app.repositories.user_repository as user_repo
import app.repositories.chat_repository as chat_repo
import app.services.chat_service as chat_service
from app.services.complaint_agent import classify_complaint
from app.services.complaint_dialogue_agent import (
    has_active_complaint_session,
    handle_complaint_turn,
    start_complaint_session,
)
from app.services.rag_service import get_answer_stream

router = APIRouter()

_COMPLAINT_CONFIDENCE_THRESHOLD = 0.60


async def _stream_response(
    user_id: str,
    user_info: Dict[str, Any],
    query: str,
    chat_id: str,
    title: str,
    metadata_filter,
) -> AsyncGenerator[str, None]:
    """
    Core SSE generator shared by the /stream endpoint.
    Handles complaint sessions (instant) and RAG (streamed tokens).
    """
    # ── Complaint dialogue turn (instant, no streaming needed) ─────────────────
    if has_active_complaint_session(chat_id):
        dialogue_reply = handle_complaint_turn(
            chat_id=chat_id,
            user_message=query,
            user_info=user_info,
        )
        if dialogue_reply is not None:
            chat_repo.add_message(chat_id, "bot", dialogue_reply)
            yield f"data: {json.dumps({'token': dialogue_reply})}\n\n"
            yield f"data: {json.dumps({'done': True, 'sources': [], 'chat_id': chat_id, 'title': title})}\n\n"
            return

    # ── New complaint detection (instant) ──────────────────────────────────────
    try:
        clf = classify_complaint(query)
        if (
            clf.get("is_complaint")
            and float(clf.get("confidence", 0)) >= _COMPLAINT_CONFIDENCE_THRESHOLD
            and clf.get("category") != "not_complaint"
        ):
            intake_prompt = start_complaint_session(
                chat_id=chat_id,
                complaint_text=query,
                classification=clf,
                user_info=user_info,
            )
            chat_repo.add_message(chat_id, "bot", intake_prompt)
            yield f"data: {json.dumps({'token': intake_prompt})}\n\n"
            yield f"data: {json.dumps({'done': True, 'sources': [], 'chat_id': chat_id, 'title': title})}\n\n"
            return
    except Exception:
        pass  # Non-critical — fall through to RAG

    # ── RAG streaming ──────────────────────────────────────────────────────────
    chat_history = chat_repo.get_recent_history(chat_id, limit=6)
    full_answer = []

    async for sse_line in get_answer_stream(
        query,
        metadata_filter=metadata_filter,
        user_info=user_info,
        chat_history=chat_history,
    ):
        # Parse the SSE line to collect the full answer for DB persistence
        try:
            payload = json.loads(sse_line.removeprefix("data: ").strip())
            if not payload.get("done"):
                full_answer.append(payload.get("token", ""))
            else:
                # Attach session info to the final done event
                payload["chat_id"] = chat_id
                payload["title"]   = title
                sse_line = f"data: {json.dumps(payload)}\n\n"
        except Exception:
            pass
        yield sse_line

    # Persist the complete answer after streaming finishes
    if full_answer:
        chat_repo.add_message(chat_id, "bot", "".join(full_answer))


# ── Chat endpoints ─────────────────────────────────────────────────────────────

@router.post("/api/chat/stream")
async def chat_stream(request: QueryRequest, current_user=Depends(get_current_user)):
    """SSE streaming chat endpoint. Returns text/event-stream."""
    user_id   = str(current_user.id)
    user_info = await fetch_profile(user_id)

    # Resolve or create the chat session BEFORE starting the stream
    # (so we can include chat_id in the done event)
    try:
        if not request.chat_id:
            title    = request.query[:50] + "..." if len(request.query) > 50 else request.query
            new_chat = chat_repo.create_chat(user_id, title)
            chat_id  = new_chat["id"]
        else:
            existing = chat_repo.get_chat_by_id_and_user(request.chat_id, user_id)
            if not existing:
                raise HTTPException(status_code=403, detail="Chat not found or access denied.")
            chat_id = request.chat_id
            title   = existing["title"]

        # Persist user message immediately (before tokens stream)
        chat_repo.add_message(chat_id, "user", request.query)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return StreamingResponse(
        _stream_response(
            user_id=user_id,
            user_info=user_info,
            query=request.query,
            chat_id=chat_id,
            title=title,
            metadata_filter=request.metadata_filter,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable nginx buffering if behind proxy
        },
    )


@router.post("/api/chat")
async def chat(request: QueryRequest, current_user=Depends(get_current_user)):
    user_id   = str(current_user.id)
    user_info = await fetch_profile(user_id)
    try:
        return await chat_service.handle_chat(
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


@router.get("/api/chats")
async def get_chats(current_user=Depends(get_current_user)):
    """Return all chat sessions for the authenticated user."""
    return chat_service.get_user_chats(str(current_user.id))


@router.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str, current_user=Depends(get_current_user)):
    success = chat_service.delete_chat(chat_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=403, detail="Chat not found or access denied.")
    return {"message": "Chat deleted successfully."}


@router.get("/api/chats/{chat_id}/messages")
async def get_messages(chat_id: str, current_user=Depends(get_current_user)):
    try:
        return chat_service.get_chat_messages(chat_id, str(current_user.id))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
