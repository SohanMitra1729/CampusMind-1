-- ═══════════════════════════════════════════════════════════════════════════════
-- CampusMind Migration 06: Persistent Bot Sessions & Atomic Vote RPC
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1. Bot Sessions Table (replaces in-memory _bot_state & _staff_state)
CREATE TABLE IF NOT EXISTS public.bot_sessions (
    chat_id TEXT PRIMARY KEY,
    state TEXT,
    data JSONB DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

ALTER TABLE public.bot_sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on bot_sessions" ON public.bot_sessions;
CREATE POLICY "Service role full access on bot_sessions" ON public.bot_sessions
    FOR ALL USING (true) WITH CHECK (true);

-- 2. Atomic Upvote Stored Procedure
CREATE OR REPLACE FUNCTION increment_complaint_vote(target_complaint_id UUID)
RETURNS INT AS $$
DECLARE
    new_count INT;
BEGIN
    UPDATE public.complaints
    SET vote_count = vote_count + 1
    WHERE id = target_complaint_id
    RETURNING vote_count INTO new_count;
    RETURN new_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
