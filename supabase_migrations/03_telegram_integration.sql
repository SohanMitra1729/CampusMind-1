-- ═══════════════════════════════════════════════════════════════════════════════
-- CampusMind Migration 03: Telegram Bot Student Profile Integration
-- ═══════════════════════════════════════════════════════════════════════════════

ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS telegram_chat_id TEXT UNIQUE;

CREATE INDEX IF NOT EXISTS idx_profiles_telegram_chat_id
    ON public.profiles (telegram_chat_id);
