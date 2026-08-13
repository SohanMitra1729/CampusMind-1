"""
main.py — CampusMind FastAPI Application Entry Point
─────────────────────────────────────────────────────
This file is intentionally minimal. It is responsible for:
  1. Creating the FastAPI app instance
  2. Registering CORS middleware
  3. Wiring up routers (each router owns its own routes)
  4. Running startup hooks (Telegram webhook registration)
  5. Starting uvicorn (for local dev)

Business logic lives in:  app/services/
Database queries live in:  app/repositories/
Route handlers live in:    app/routers/
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, chat, notices, complaints, webhooks
from telegram_bot import setup_webhook
from staff_bot import setup_staff_webhook

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CampusMind API",
    description="AI-powered campus assistant — RAG, complaints, notices, Telegram bots.",
    version="2.0.0",
)

# ── Startup hook: register Telegram webhooks ───────────────────────────────────

@app.on_event("startup")
async def on_startup():
    await setup_webhook()
    await setup_staff_webhook()

# ── CORS ───────────────────────────────────────────────────────────────────────

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

# ── Routers ────────────────────────────────────────────────────────────────────
# Each router file owns its routes. main.py only wires them together.

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(notices.router)
app.include_router(complaints.router)
app.include_router(webhooks.router)

# ── Dev server ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
