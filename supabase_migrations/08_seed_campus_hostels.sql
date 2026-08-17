-- ═══════════════════════════════════════════════════════════════════════════════
-- CampusMind Migration 08: Seed Campus Hostels & Mess Linkages
-- ═══════════════════════════════════════════════════════════════════════════════
-- Seeds all 16 campus hostels (Boys & Girls), mixed room sharing setups (ARRAY),
-- batch years, mess assignments (including shared messes for 9A/9B and 9C/9D), and aliases.
-- ═══════════════════════════════════════════════════════════════════════════════

INSERT INTO public.hostels (
    name,
    code,
    gender,
    target_years,
    sharing_types,
    sharing_description,
    mess_id,
    mess_name,
    aliases
) VALUES
-- ── BOYS HOSTELS ─────────────────────────────────────────────────────────────
(
    'Boys Hostel 3 (BH-3)',
    'BH3',
    'boys',
    '1st Year BTech',
    ARRAY[1],
    '1-share (Single room)',
    'mess_bh3',
    'BH-3 Mess (Individual)',
    ARRAY['bh3', 'bh-3', 'hostel 3', 'boys hostel 3', 'h3']
),
(
    'Aryabhatta Hostel',
    'ARYABHATTA',
    'boys',
    '1st Year BTech',
    ARRAY[2],
    '2-share (Double room)',
    'mess_aryabhatta',
    'Aryabhatta Mess (Individual)',
    ARRAY['aryabhatta', 'aryabatta', 'arya', 'aryabhata']
),
(
    'Boys Hostel 1 (BH-1)',
    'BH1',
    'boys',
    '2nd Year BTech',
    ARRAY[3],
    '3-share (Triple room)',
    'mess_bh1',
    'BH-1 Mess (Individual)',
    ARRAY['bh1', 'bh-1', 'hostel 1', 'boys hostel 1', 'h1']
),
(
    'Boys Hostel 2 (BH-2)',
    'BH2',
    'boys',
    '2nd Year BTech',
    ARRAY[3],
    '3-share (Triple room)',
    'mess_bh2',
    'BH-2 Mess (Individual)',
    ARRAY['bh2', 'bh-2', 'hostel 2', 'boys hostel 2', 'h2']
),
(
    'Boys Hostel 8 (BH-8)',
    'BH8',
    'boys',
    '2nd Year BTech',
    ARRAY[3],
    '3-share (Triple room)',
    'mess_bh8',
    'BH-8 Mess (Individual)',
    ARRAY['bh8', 'bh-8', 'hostel 8', 'boys hostel 8', 'h8']
),
(
    'Boys Hostel 4 (BH-4)',
    'BH4',
    'boys',
    '2nd & 4th Year BTech',
    ARRAY[1, 3],
    '2nd yrs: 3-share, 4th yrs: single share',
    'mess_bh4',
    'BH-4 Mess (Individual)',
    ARRAY['bh4', 'bh-4', 'hostel 4', 'boys hostel 4', 'h4']
),
(
    'Boys Hostel 6 (BH-6)',
    'BH6',
    'boys',
    '3rd & 4th Year BTech',
    ARRAY[1, 3],
    '3rd yrs: 3-share, 4th yrs: single share',
    'mess_bh6',
    'BH-6 Mess (Individual)',
    ARRAY['bh6', 'bh-6', 'hostel 6', 'boys hostel 6', 'h6']
),
(
    'Boys Hostel 7 (BH-7)',
    'BH7',
    'boys',
    '3rd & 4th Year BTech',
    ARRAY[1, 3],
    '3rd yrs: 3-share, 4th yrs: single share',
    'mess_bh7',
    'BH-7 Mess (Individual)',
    ARRAY['bh7', 'bh-7', 'hostel 7', 'boys hostel 7', 'h7']
),
(
    'BH-9A (Jagadish Chandra Bose)',
    'BH9A',
    'boys',
    '3rd Year BTech',
    ARRAY[2],
    '3rd yrs: 2-share',
    'mess_bh9ab_shared',
    'BH-9A/9B Shared Mess',
    ARRAY['bh9a', 'bh-9a', '9a', 'jcb', 'jagadish chandra bose', 'jagadish changrabose']
),
(
    'BH-9B (Srinivasa Ramanujan)',
    'BH9B',
    'boys',
    '1st Year BTech',
    ARRAY[2],
    '1st yrs: 2-share',
    'mess_bh9ab_shared',
    'BH-9A/9B Shared Mess',
    ARRAY['bh9b', 'bh-9b', '9b', 'ramanujan', 'srinivasa ramanujan']
),
(
    'Boys Hostel 9C (BH-9C)',
    'BH9C',
    'boys',
    '4th Year BTech',
    ARRAY[1],
    '4th yrs: single share',
    'mess_bh9cd_shared',
    'BH-9C/9D Shared Mess',
    ARRAY['bh9c', 'bh-9c', '9c', 'hostel 9c']
),
(
    'Boys Hostel 9D (BH-9D)',
    'BH9D',
    'boys',
    '4th Year BTech',
    ARRAY[1],
    '4th yrs: single share',
    'mess_bh9cd_shared',
    'BH-9C/9D Shared Mess',
    ARRAY['bh9d', 'bh-9d', '9d', 'hostel 9d']
),

-- ── GIRLS HOSTELS ────────────────────────────────────────────────────────────
(
    'Girls Hostel 1 (GH-1)',
    'GH1',
    'girls',
    '3rd & 4th Year BTech',
    ARRAY[2, 3],
    '3rd & 4th yrs: 2-share / 3-share',
    'mess_gh1',
    'GH-1 Mess (Individual)',
    ARRAY['gh1', 'gh-1', 'hostel gh1', 'girls hostel 1', 'gh 1']
),
(
    'Girls Hostel 2 (GH-2)',
    'GH2',
    'girls',
    '2nd & 3rd Year BTech',
    ARRAY[3],
    '2nd & 3rd yrs: 3-share (Triple room)',
    'mess_gh2',
    'GH-2 Mess (Individual)',
    ARRAY['gh2', 'gh-2', 'hostel gh2', 'girls hostel 2', 'gh 2']
),
(
    'Girls Hostel 3 (GH-3)',
    'GH3',
    'girls',
    '1st Year BTech',
    ARRAY[2],
    '1st yrs: 2-share (Double room)',
    'mess_gh3',
    'GH-3 Mess (Individual)',
    ARRAY['gh3', 'gh-3', 'hostel gh3', 'girls hostel 3', 'gh 3']
),
(
    'Girls Hostel 4 (GH-4)',
    'GH4',
    'girls',
    '2nd, 3rd & 4th Year BTech',
    ARRAY[1, 2],
    '2nd & 3rd yrs: 2-share, 4th yrs: single share',
    'mess_gh4',
    'GH-4 Mess (Individual)',
    ARRAY['gh4', 'gh-4', 'hostel gh4', 'girls hostel 4', 'gh 4']
)

ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    gender = EXCLUDED.gender,
    target_years = EXCLUDED.target_years,
    sharing_types = EXCLUDED.sharing_types,
    sharing_description = EXCLUDED.sharing_description,
    mess_id = EXCLUDED.mess_id,
    mess_name = EXCLUDED.mess_name,
    aliases = EXCLUDED.aliases;
