-- ═══════════════════════════════════════════════════════════════════════════════
-- CampusMind Complete Production Database Schema
-- ═══════════════════════════════════════════════════════════════════════════════
-- Run this script in the Supabase SQL Editor for a single-click database setup.
-- ═══════════════════════════════════════════════════════════════════════════════

-- ── 1. Extensions ─────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;

-- ── 2. Vector Documents Table (pgvector 3072 + FTS) ──────────────────────────
CREATE TABLE IF NOT EXISTS public.documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT,
    metadata JSONB,
    embedding VECTOR(3072),
    fts TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

CREATE INDEX IF NOT EXISTS idx_documents_fts ON public.documents USING GIN (fts);
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on documents" ON public.documents;
CREATE POLICY "Service role full access on documents" ON public.documents
    FOR ALL USING (true) WITH CHECK (true);

-- ── 3. Student Profiles Table ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
    name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    scholar_id VARCHAR(7) UNIQUE NOT NULL,
    telegram_chat_id TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    CONSTRAINT scholar_id_format CHECK (scholar_id ~ '^\d{7}$')
);

CREATE INDEX IF NOT EXISTS idx_profiles_telegram_chat_id ON public.profiles (telegram_chat_id);
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public profiles are viewable by everyone" ON public.profiles;
DROP POLICY IF EXISTS "Users can insert their own profile" ON public.profiles;
DROP POLICY IF EXISTS "Users can update their own profile" ON public.profiles;

CREATE POLICY "Public profiles are viewable by everyone" ON public.profiles FOR SELECT USING (true);
CREATE POLICY "Users can insert their own profile" ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "Users can update their own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- Trigger to auto-create profile row on auth user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, name, username, email, scholar_id)
    VALUES (
        new.id,
        COALESCE(new.raw_user_meta_data->>'name', ''),
        COALESCE(new.raw_user_meta_data->>'username', ''),
        new.email,
        COALESCE(new.raw_user_meta_data->>'scholar_id', '')
    );
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ── 4. RAG Chat Sessions & Messages ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.chats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own chats" ON public.chats;
DROP POLICY IF EXISTS "Users can insert their own chats" ON public.chats;
DROP POLICY IF EXISTS "Users can delete their own chats" ON public.chats;

CREATE POLICY "Users can view their own chats" ON public.chats FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own chats" ON public.chats FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete their own chats" ON public.chats FOR DELETE USING (auth.uid() = user_id);

CREATE TABLE IF NOT EXISTS public.messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    chat_id UUID REFERENCES public.chats(id) ON DELETE CASCADE NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'bot')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view messages of their chats" ON public.messages;
DROP POLICY IF EXISTS "Users can insert messages into their chats" ON public.messages;

CREATE POLICY "Users can view messages of their chats" ON public.messages
    FOR SELECT USING (EXISTS (SELECT 1 FROM public.chats WHERE chats.id = messages.chat_id AND chats.user_id = auth.uid()));

CREATE POLICY "Users can insert messages into their chats" ON public.messages
    FOR INSERT WITH CHECK (EXISTS (SELECT 1 FROM public.chats WHERE chats.id = messages.chat_id AND chats.user_id = auth.uid()));

-- ── 5. Admin Notices & In-App Notifications ──────────────────────────────────
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

CREATE POLICY "Service role full access on notices" ON public.notices FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on user_notifications" ON public.user_notifications FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Users can view their own notifications" ON public.user_notifications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update their own notifications" ON public.user_notifications FOR UPDATE USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_user_notifications_user_id ON public.user_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_user_notifications_is_read ON public.user_notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notices_created_at ON public.notices(created_at DESC);

-- ── 6. Hostels & Staff Members ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.hostels (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL
);

ALTER TABLE public.hostels ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public hostels readable" ON public.hostels;
DROP POLICY IF EXISTS "Service role full access on hostels" ON public.hostels;

CREATE POLICY "Public hostels readable" ON public.hostels FOR SELECT USING (true);
CREATE POLICY "Service role full access on hostels" ON public.hostels FOR ALL USING (true) WITH CHECK (true);

INSERT INTO public.hostels (name, code) VALUES
    ('Hostel 1', 'H1'),
    ('Hostel 2', 'H2'),
    ('Hostel 3', 'H3'),
    ('Hostel 4', 'H4'),
    ('Boys Hostel', 'BH'),
    ('Girls Hostel', 'GH')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.staff_members (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT,
    phone_number TEXT UNIQUE,
    telegram_chat_id TEXT UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('electrical', 'cleaning', 'mess_manager', 'watchmen')),
    hostel_id UUID REFERENCES public.hostels(id) ON DELETE SET NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

ALTER TABLE public.staff_members ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on staff_members" ON public.staff_members;
CREATE POLICY "Service role full access on staff_members" ON public.staff_members FOR ALL USING (true) WITH CHECK (true);

CREATE TABLE IF NOT EXISTS public.staff_rooms (
    staff_id UUID REFERENCES public.staff_members(id) ON DELETE CASCADE,
    room_number TEXT NOT NULL,
    PRIMARY KEY (staff_id, room_number)
);

ALTER TABLE public.staff_rooms ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on staff_rooms" ON public.staff_rooms;
CREATE POLICY "Service role full access on staff_rooms" ON public.staff_rooms FOR ALL USING (true) WITH CHECK (true);

-- ── 7. Complaints & Upvoting ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.complaints (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    scholar_id VARCHAR(7),
    student_name TEXT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'dismissed')),
    hostel_details JSONB DEFAULT '{}',
    hostel_id UUID REFERENCES public.hostels(id) ON DELETE SET NULL,
    room_number TEXT,
    vote_count INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

ALTER TABLE public.complaints ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on complaints" ON public.complaints;
DROP POLICY IF EXISTS "Students can view their own complaints" ON public.complaints;

CREATE POLICY "Service role full access on complaints" ON public.complaints FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Students can view their own complaints" ON public.complaints FOR SELECT USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_complaints_hostel_room ON public.complaints (hostel_id, room_number);
CREATE INDEX IF NOT EXISTS idx_complaints_user_id ON public.complaints (user_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON public.complaints (status);

CREATE TABLE IF NOT EXISTS public.complaint_votes (
    complaint_id UUID REFERENCES public.complaints(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    scholar_id VARCHAR(7),
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (complaint_id, user_id)
);

ALTER TABLE public.complaint_votes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on complaint_votes" ON public.complaint_votes;
CREATE POLICY "Service role full access on complaint_votes" ON public.complaint_votes FOR ALL USING (true) WITH CHECK (true);

-- ── 8. Hybrid RRF Search Stored Procedure ───────────────────────────────────
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(3072),
    match_count INT,
    filter JSONB DEFAULT '{}',
    full_text_weight FLOAT DEFAULT 1.0,
    semantic_weight FLOAT DEFAULT 1.0,
    rrf_k INT DEFAULT 50
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE sql
AS $$
WITH full_text AS (
    SELECT
        d.id,
        row_number() OVER (ORDER BY ts_rank_cd(d.fts, websearch_to_tsquery('english', query_text)) DESC) AS rank_ix
    FROM
        public.documents d
    WHERE
        d.fts @@ websearch_to_tsquery('english', query_text)
        AND d.metadata @> filter
),
semantic AS (
    SELECT
        d.id,
        row_number() OVER (ORDER BY d.embedding <=> query_embedding) AS rank_ix
    FROM
        public.documents d
    WHERE
        d.metadata @> filter
)
SELECT
    documents.id,
    documents.content,
    documents.metadata,
    (COALESCE(1.0 / (rrf_k + full_text.rank_ix), 0.0) * full_text_weight +
     COALESCE(1.0 / (rrf_k + semantic.rank_ix), 0.0) * semantic_weight) AS similarity
FROM
    full_text
    FULL OUTER JOIN semantic
        ON full_text.id = semantic.id
    JOIN public.documents
        ON COALESCE(full_text.id, semantic.id) = documents.id
ORDER BY similarity DESC
LIMIT match_count;
$$;
