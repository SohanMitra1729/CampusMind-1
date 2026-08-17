-- ═══════════════════════════════════════════════════════════════════════════════
-- CampusMind Migration 07: Facility Topology, Staff Roles & Complaint Scopes
-- ═══════════════════════════════════════════════════════════════════════════════
-- 1. Enhances hostels with dynamic sharing_type, mess_id, mess_name
-- 2. Adds staff_role, scope, and mess_id to complaints
-- 3. Updates staff_members role CHECK constraint to include 'maintenance' & mess_id
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1. Hostels Table Updates
ALTER TABLE public.hostels
    ADD COLUMN IF NOT EXISTS gender TEXT CHECK (gender IN ('boys', 'girls', 'co-ed')),
    ADD COLUMN IF NOT EXISTS target_years TEXT,
    ADD COLUMN IF NOT EXISTS sharing_types INT[] DEFAULT '{1}',
    ADD COLUMN IF NOT EXISTS sharing_description TEXT,
    ADD COLUMN IF NOT EXISTS mess_id TEXT,
    ADD COLUMN IF NOT EXISTS mess_name TEXT,
    ADD COLUMN IF NOT EXISTS aliases TEXT[] DEFAULT '{}';

-- 2. Complaints Table Updates
ALTER TABLE public.complaints
    ADD COLUMN IF NOT EXISTS staff_role TEXT
        CHECK (staff_role IN ('electrical', 'cleaning', 'maintenance', 'mess_manager', 'watchmen')),
    ADD COLUMN IF NOT EXISTS scope TEXT
        CHECK (scope IN ('MESS', 'ROOM_SHARED', 'ROOM_INDIVIDUAL', 'COMMON_AREA')) DEFAULT 'COMMON_AREA',
    ADD COLUMN IF NOT EXISTS mess_id TEXT;

CREATE INDEX IF NOT EXISTS idx_complaints_staff_role ON public.complaints (staff_role);
CREATE INDEX IF NOT EXISTS idx_complaints_scope ON public.complaints (scope);
CREATE INDEX IF NOT EXISTS idx_complaints_mess_id ON public.complaints (mess_id);

-- 3. Staff Members Table Updates
ALTER TABLE public.staff_members
    ADD COLUMN IF NOT EXISTS mess_id TEXT;

ALTER TABLE public.staff_members
    DROP CONSTRAINT IF EXISTS staff_members_role_check;

ALTER TABLE public.staff_members
    ADD CONSTRAINT staff_members_role_check
        CHECK (role IN ('electrical', 'cleaning', 'maintenance', 'mess_manager', 'watchmen'));
