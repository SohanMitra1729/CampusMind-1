"""
app/routers/webhooks.py — Telegram Bot Webhook Routes
───────────────────────────────────────────────────────
Handles:
  POST /api/telegram/webhook       ← student bot (telegram_bot.py)
  POST /api/staff/telegram/webhook ← staff bot (staff_bot.py)

Both endpoints return 200 immediately and process the update in a BackgroundTask
so Telegram's webhook timeout (5s) is never exceeded.
"""

from fastapi import APIRouter, BackgroundTasks, Body

from rag import supabase
from telegram_bot import handle_update
from staff_bot import handle_staff_update

router = APIRouter()


@router.post("/api/telegram/webhook")
async def telegram_webhook(
    background_tasks: BackgroundTasks,
    update: dict = Body(...),
):
    """Student bot webhook — returns 200 immediately; processing runs in background."""
    background_tasks.add_task(handle_update, update, supabase)
    return {"ok": True}


@router.post("/api/staff/telegram/webhook")
async def staff_telegram_webhook(
    background_tasks: BackgroundTasks,
    update: dict = Body(...),
):
    """Staff bot webhook — returns 200 immediately; processing runs in background."""
    background_tasks.add_task(handle_staff_update, update, supabase)
    return {"ok": True}
