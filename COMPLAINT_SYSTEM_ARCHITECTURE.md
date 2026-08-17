# CampusMind: Intelligent Complaint & Facility Management System

## 1. Campus Facility & Topology Model

Campus hostels are heterogeneous in room capacity, layout, and dining facilities. The system models this through dynamic database attributes rather than hardcoded assumptions:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Campus Facility Topology                        │
├─────────────────┬──────────────┬───────────────────────────────────────┤
│ Hostel Building │ Room Sharing │ Assigned Dining Hall (Mess ID)        │
├─────────────────┼──────────────┼───────────────────────────────────────┤
│ BH-3            │ 1 (Single)   │ mess_bh3 (Standalone)                 │
│ Aryabhatta      │ 2 (Double)   │ mess_aryabhatta (Standalone)          │
│ BH-4            │ 3 (Triple)   │ mess_bh4 (Standalone)                 │
│ BH-8            │ 3 (Triple)   │ mess_bh8 (Standalone)                 │
│ BH-9A           │ 3 (Triple)   │ mess_bh9_shared ──┐ (Shared Mess)     │
│ BH-9B           │ 3 (Triple)   │ mess_bh9_shared ──┘                   │
└─────────────────┴──────────────┴───────────────────────────────────────┘
```

---

## 2. Staff Roles & Department Dispatch

The system routes complaints across **5 dedicated ground staff roles** plus an **Administration** bucket for non-hostel issues:

| Role Code | Icon | Department / Scope |
| :--- | :---: | :--- |
| `electrical` | ⚡ | Lights, ceiling fans, wiring, switches, sockets, inverter, power supply |
| `cleaning` | 🧹 | Waste disposal, room/corridor sweeping, sanitation, pest control, washroom cleaning |
| `maintenance` | 🛠️ | Furniture (bed, study table, chair, wardrobe), plumbing (taps, drains, pipes, flush), doors, windows, locks, civil work |
| `mess_manager` | 🍽️ | Meal timings, food quality, raw/cold food, kitchen hygiene, dining hall water |
| `watchmen` | 🔒 | Security, gate entry/exit, curfew, theft, outsiders, perimeter safety |
| *Unassigned* (`None`) | 🏛️ | Academic marks, fees, administrative documents, bus transport |

---

## 3. Complaint Scope & Deduplication Matrix

Every complaint is classified into one of **4 clear boundary scopes** to eliminate ambiguity:

```
                              Incoming Complaint
                                      │
        ┌───────────────────┬─────────┴─────────┬───────────────────┐
        ▼                   ▼                   ▼                   ▼
    [ MESS ]        [ ROOM_SHARED ]    [ ROOM_INDIVIDUAL ]   [ COMMON_AREA ]
  Scoped to:          Scoped to:           Scoped to:          Scoped to:
   mess_id       hostel_id + room_no    student + room_no   hostel_id + text
        │                   │                   │                   │
  Group / Upvote     Roommate Upvote      Separate Ticket     Direct Staff
  across hostels    on shared fixtures     per accessory        Dispatch
```

### Detailed Scope Rules:

| Scope | Applicable Assets | Grouping & Deduplication Strategy |
| :--- | :--- | :--- |
| **`MESS`** | Food quality, delayed meal, canteen hygiene, mess drinking water | **Grouped / Upvotable across linked hostels.** <br>Complaints from BH-9A and BH-9B share the same `mess_bh9_shared` pool. |
| **`ROOM_SHARED`** | Ceiling fan, tube light, room switchboard, room main door | **Roommate Corroboration.** <br>If Roommate 1 reports a broken fan in Room 204, Roommate 2's report becomes an upvote/priority boost on Ticket #1. |
| **`ROOM_INDIVIDUAL`** | Bed frame, mattress, study table, chair, personal wardrobe | **Individual Repair Tickets.** <br>Each student in a 2-share or 3-share room gets an independent ticket for their assigned furniture. |
| **`COMMON_AREA`** | Floor washrooms, geysers, corridor lights, water coolers, stairs | **Direct Staff Dispatch.** <br>No aggressive merging to prevent confusing different floor washrooms. Staff receives the exact student description on Telegram. |

---

## 4. Student Spam & Cooldown Prevention

To prevent students from creating duplicate tickets for the same issue with different wording:
1. **Self-Ticket Check:** Before creating a ticket, check if the student has an active `open` or `in_progress` ticket for that asset.
2. **Conversational Feedback:** Instead of creating a duplicate, the AI informs the student:
   > *"You already have an active ticket **#1042 ('Ceiling fan repair in Room 204')** filed 20 minutes ago (Status: In Progress / Assigned to Electrician). I have added your update to the ticket notes."*

---

## 5. Database Schema Blueprint

### 5.1 Hostels Table (`public.hostels`)
```sql
CREATE TABLE public.hostels (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    sharing_type INT DEFAULT 1,              -- 1 (single), 2 (double), 3 (triple)
    mess_id TEXT NOT NULL,                   -- e.g. 'mess_bh3', 'mess_bh9_shared'
    mess_name TEXT NOT NULL                  -- e.g. 'BH-3 Mess', 'BH-9 Shared Mess'
);
```

### 5.2 Complaints Table (`public.complaints`)
```sql
CREATE TABLE public.complaints (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    scholar_id VARCHAR(7),
    student_name TEXT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    staff_role TEXT CHECK (staff_role IN ('electrical', 'cleaning', 'maintenance', 'mess_manager', 'watchmen')),
    scope TEXT NOT NULL CHECK (scope IN ('MESS', 'ROOM_SHARED', 'ROOM_INDIVIDUAL', 'COMMON_AREA')) DEFAULT 'COMMON_AREA',
    mess_id TEXT,                            -- Populated when scope = 'MESS'
    hostel_id UUID REFERENCES public.hostels(id) ON DELETE SET NULL,
    room_number TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'dismissed')),
    vote_count INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);
```

### 5.3 Staff Members Table (`public.staff_members`)
```sql
CREATE TABLE public.staff_members (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT,
    phone_number TEXT UNIQUE,
    telegram_chat_id TEXT UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('electrical', 'cleaning', 'maintenance', 'mess_manager', 'watchmen')),
    hostel_id UUID REFERENCES public.hostels(id) ON DELETE SET NULL,
    mess_id TEXT,                            -- Set for mess_manager roles
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);
```

---

## 6. End-to-End Execution Flow

```
1. Student types in Chat / Telegram: "Dinner food in mess is cold"
   │
2. AI Pipeline fetches Student Profile:
   - Scholar ID: 2212001
   - Hostel: BH-9A (sharing_type: 3, mess_id: 'mess_bh9_shared')
   │
3. LLM Classification & Scope Tagging:
   - Category: "mess"
   - Staff Role: "mess_manager"
   - Scope: "MESS"
   - Target Mess: "mess_bh9_shared"
   │
4. Similarity & Deduplication Gate:
   - Check open tickets where mess_id = 'mess_bh9_shared' within last 24h.
   - If match found: Prompt student with Upvote Option / Corroboration.
   - If new: Save complaint to DB with scope='MESS' and mess_id='mess_bh9_shared'.
   │
5. Staff Dispatch:
   - Send instant alert to Mess Manager of 'mess_bh9_shared' on Telegram.
   - Live badge visible in Web Admin Portal.
```
