-- ═══════════════════════════════════════════════════════════════════════════════
-- CampusMind Migration 02: Notices & User Notifications
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1. Notices Table (Admin notices from PDF ingestion or text)
CREATE TABLE IF NOT EXISTS public.notices (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    notice_type TEXT NOT NULL DEFAULT 'general',
    source_type TEXT NOT NULL DEFAULT 'pdf',
    source_file TEXT,
    scholar_ids TEXT[] DEFAULT '{}',
    is_broadcast BOOLEAN DEFAULT FALSE,
    notified_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 2. User Notifications Table (Targeted per-student inbox delivery)
CREATE TABLE IF NOT EXISTS public.user_notifications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    notice_id UUID REFERENCES public.notices(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    scholar_id VARCHAR(7),
    notification_title TEXT NOT NULL,
    notification_message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

ALTER TABLE public.notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_notifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on notices" ON public.notices;
DROP POLICY IF EXISTS "Service role full access on user_notifications" ON public.user_notifications;
DROP POLICY IF EXISTS "Users can view their own notifications" ON public.user_notifications;
DROP POLICY IF EXISTS "Users can update their own notifications" ON public.user_notifications;

CREATE POLICY "Service role full access on notices" ON public.notices
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on user_notifications" ON public.user_notifications
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Users can view their own notifications" ON public.user_notifications
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own notifications" ON public.user_notifications
    FOR UPDATE USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_user_notifications_user_id ON public.user_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_user_notifications_is_read ON public.user_notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notices_created_at ON public.notices(created_at DESC);
