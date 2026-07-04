-- Migration: Add hostels, staff_members, staff_rooms, and extend complaints
-- Run this SQL in Supabase SQL editor

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. HOSTELS TABLE
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hostels (
    id   UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL  -- e.g., H1, H2, BH1
);

-- RLS: anyone can read hostel names (needed by the frontend dropdown)
ALTER TABLE hostels ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public hostels readable" ON hostels;
CREATE POLICY "Public hostels readable" ON hostels
    FOR SELECT USING (true);

-- Service role can insert/update/delete hostels (backend only)
DROP POLICY IF EXISTS "Service role full access on hostels" ON hostels;
CREATE POLICY "Service role full access on hostels" ON hostels
    USING (true)
    WITH CHECK (true);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. STAFF MEMBERS TABLE
--    Staff are NOT Supabase auth users — they register via Telegram bot.
--    The backend always connects with the SERVICE KEY so no per-row auth needed.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS staff_members (
    id               UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
    name             TEXT,
    phone_number     TEXT    UNIQUE,
    telegram_chat_id TEXT    UNIQUE,   -- Telegram chat ID stored as text (e.g. "123456789")
    role             TEXT    NOT NULL  CHECK (role IN ('electrical','cleaning','mess_manager','watchmen')),
    hostel_id        UUID    REFERENCES hostels(id) ON DELETE SET NULL,
    active           BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMPTZ DEFAULT now()
);

-- RLS: backend service role gets full access; no public read needed
ALTER TABLE staff_members ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on staff_members" ON staff_members;
CREATE POLICY "Service role full access on staff_members" ON staff_members
    USING (true)
    WITH CHECK (true);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. STAFF ROOMS TABLE (optional per-room assignment)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS staff_rooms (
    staff_id    UUID REFERENCES staff_members(id) ON DELETE CASCADE,
    room_number TEXT NOT NULL,
    PRIMARY KEY (staff_id, room_number)
);

ALTER TABLE staff_rooms ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on staff_rooms" ON staff_rooms;
CREATE POLICY "Service role full access on staff_rooms" ON staff_rooms
    USING (true)
    WITH CHECK (true);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. EXTEND COMPLAINTS TABLE WITH LOCATION FIELDS
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE complaints ADD COLUMN IF NOT EXISTS hostel_id   UUID REFERENCES hostels(id) ON DELETE SET NULL;
ALTER TABLE complaints ADD COLUMN IF NOT EXISTS room_number TEXT;

-- Composite index for fast routing queries (hostel + room)
CREATE INDEX IF NOT EXISTS idx_complaints_hostel_room ON complaints (hostel_id, room_number);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. SEED SAMPLE HOSTELS (optional — edit or remove as needed)
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO hostels (name, code) VALUES
    ('Hostel 1', 'H1'),
    ('Hostel 2', 'H2'),
    ('Hostel 3', 'H3'),
    ('Hostel 4', 'H4'),
    ('Boys Hostel', 'BH'),
    ('Girls Hostel', 'GH')
ON CONFLICT (code) DO NOTHING;
