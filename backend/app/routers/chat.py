"""
app/routers/chat.py — Chat & RAG Routes
────────────────────────────────────────
Handles:
  POST   /api/chat
  GET    /api/chats
  DELETE /api/chats/{chat_id}
  GET    /api/chats/{chat_id}/messages
"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Depends

from app.core.security import get_current_user
from app.core.deps import fetch_profile
from app.schemas.chat import QueryRequest
import app.repositories.user_repository as user_repo
import app.services.chat_service as chat_service

router = APIRouter()


# ── Chat endpoints ─────────────────────────────────────────────────────────────

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
