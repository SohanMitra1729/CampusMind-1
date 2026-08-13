-- ═══════════════════════════════════════════════════════════════════════════════
-- CampusMind Migration 04: Hostels, Staff Members, Complaints & Upvotes
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1. Hostels Directory
CREATE TABLE IF NOT EXISTS public.hostels (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL
);

ALTER TABLE public.hostels ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public hostels readable" ON public.hostels;
DROP POLICY IF EXISTS "Service role full access on hostels" ON public.hostels;

CREATE POLICY "Public hostels readable" ON public.hostels
    FOR SELECT USING (true);

CREATE POLICY "Service role full access on hostels" ON public.hostels
    FOR ALL USING (true) WITH CHECK (true);

-- Seed default hostels
INSERT INTO public.hostels (name, code) VALUES
    ('Hostel 1', 'H1'),
    ('Hostel 2', 'H2'),
    ('Hostel 3', 'H3'),
    ('Hostel 4', 'H4'),
    ('Boys Hostel', 'BH'),
    ('Girls Hostel', 'GH')
ON CONFLICT (code) DO NOTHING;

-- 2. Staff Members Table (Registered via Staff Telegram Bot)
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
CREATE POLICY "Service role full access on staff_members" ON public.staff_members
    FOR ALL USING (true) WITH CHECK (true);

-- 3. Staff Rooms (Optional per-room assignments)
CREATE TABLE IF NOT EXISTS public.staff_rooms (
    staff_id UUID REFERENCES public.staff_members(id) ON DELETE CASCADE,
    room_number TEXT NOT NULL,
    PRIMARY KEY (staff_id, room_number)
);

ALTER TABLE public.staff_rooms ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on staff_rooms" ON public.staff_rooms;
CREATE POLICY "Service role full access on staff_rooms" ON public.staff_rooms
    FOR ALL USING (true) WITH CHECK (true);

-- 4. Complaints Table
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

CREATE POLICY "Service role full access on complaints" ON public.complaints
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Students can view their own complaints" ON public.complaints
    FOR SELECT USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_complaints_hostel_room ON public.complaints (hostel_id, room_number);
CREATE INDEX IF NOT EXISTS idx_complaints_user_id ON public.complaints (user_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON public.complaints (status);

-- 5. Complaint Upvotes Table (Deduplication per student)
CREATE TABLE IF NOT EXISTS public.complaint_votes (
    complaint_id UUID REFERENCES public.complaints(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    scholar_id VARCHAR(7),
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (complaint_id, user_id)
);

ALTER TABLE public.complaint_votes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on complaint_votes" ON public.complaint_votes;
CREATE POLICY "Service role full access on complaint_votes" ON public.complaint_votes
    FOR ALL USING (true) WITH CHECK (true);
