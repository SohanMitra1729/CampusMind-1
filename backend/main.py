"""
main.py — CampusMind FastAPI Application Entry Point
─────────────────────────────────────────────────────
Minimal entry point:
  1. Lifespan context manager for startup/shutdown hooks
  2. CORS middleware registration
  3. Domain exception handling
  4. Wiring routers
  5. Running Uvicorn dev server
"""

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.core.logger import logger
from app.routers import auth, chat, notices, complaints, webhooks
from app.services.telegram_bot import setup_webhook
from app.services.staff_bot import setup_staff_webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager replacing deprecated @app.on_event."""
    logger.info("CampusMind API starting up...")
    await setup_webhook()
    await setup_staff_webhook()
    yield
    logger.info("CampusMind API shutting down...")


app = FastAPI(
    title="CampusMind API",
    description="AI-powered campus assistant — RAG, complaints, notices, Telegram bots.",
    version="2.0.0",
    lifespan=lifespan,
)

# ── Global Exception Handlers ──────────────────────────────────────────────────
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ── CORS Middleware ───────────────────────────────────────────────────────────
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

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(notices.router)
app.include_router(complaints.router)
app.include_router(webhooks.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
