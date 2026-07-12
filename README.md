# CampusMind

CampusMind is an AI-powered campus and hostel management platform for universities. It combines a Retrieval-Augmented Generation (RAG) knowledge base, agentic LLM workflows, a dual Telegram bot system (students + staff), and real-time complaint routing to create a fully automated campus experience.

---

## ✨ Core Features

### 🤖 Intelligent RAG Assistant
- **Hybrid Search:** Combines semantic vector search (Google Gemini embeddings) with full-text search (PostgreSQL `tsvector`) via Reciprocal Rank Fusion (RRF) for highly accurate document retrieval.
- **Persistent Chat:** ChatGPT-style memory — conversations are saved to the database and the AI maintains context across sessions (sliding window history).
- **Personalized Context:** Identifies the logged-in student to answer personalized queries (e.g., "What is my SGPA?").

---

### 📢 Agentic Notice Workflow
- **Smart Classification:** Documents uploaded by admins are auto-classified using Groq (Llama 3.3-70B).
- **Targeted Delivery:** Automatically extracts Scholar IDs from PDFs via regex to send personalized in-app notifications.
- **Telegram Push:** Students instantly receive Telegram notifications when notices relevant to them are published.
- **OCR + Table Support:** `pdf_processor.py` handles text PDFs, scanned documents (OCR), and tabular PDFs for full knowledge base coverage.

---

### 📝 AI-Agentic Complaint & Grievance System
- **Automatic Classification:** Every complaint is classified by an LLM agent into: `hostel`, `academic`, `mess`, `facility`, `transport`, `admin`, or `general`.
- **Smart Staff Role Assignment:** The LLM agent directly determines which staff role should handle the complaint based on the actual problem keywords — not just the category:
  - ⚡ `electrical` — lights, fans, power, switches, wiring
  - 🧹 `cleaning` — garbage, sanitation, dirty bathrooms, pests
  - 🍽️ `mess_manager` — food quality, meal timings, canteen
  - 🔒 `watchmen` — security, gate, outsiders, theft
- **Smart Location Capture:**
  - Hostel dropdown is always shown (required).
  - Room number field is **auto-shown** only when the AI agent detects the complaint is room-specific (e.g., "my room fan is broken").
  - Hostel-wide complaints (e.g., "mess food is bad") skip the room field entirely.
- **Similar Complaint Grouping:** Finds related open complaints using keyword overlap — students can upvote existing issues instead of duplicating them.
- **Admin Dashboard:** Administrators can view, filter, and update complaint status (Open → In Progress → Resolved → Dismissed).

---

### 👷 Staff Telegram Bot (NEW)
A dedicated second Telegram bot for hostel and facility staff members.

- **Self-Registration:** Staff register via `/start` with their phone number, hostel assignment, and role — no admin intervention required.
- **Four Supported Roles:** `electrical`, `cleaning`, `mess_manager`, `watchmen`.
- **Instant Complaint Forwarding:** When a complaint is submitted, it is automatically forwarded to the matching staff member(s) via Telegram, with complaint details, hostel name, and room number (if applicable).
- **Two-Pass Routing:** First tries exact hostel match, then falls back to any staff of the correct role to ensure no complaint goes unnoticed.
- **Inline Acknowledgement:** Staff tap ✅ Acknowledged or ✔️ Resolved buttons directly in Telegram to update the complaint status in real-time.
- **Status Check:** `/mystatus` lets staff view their current registration.

---

### 📱 Student Telegram Bot
- **Account Linking:** Securely link your 7-digit Scholar ID to your Telegram account via `/start`.
- **Instant Access:** Ask questions, get notifications, file complaints, and track status — all from Telegram.
- **Commands:** `/complaint`, `/mycomplaints`, `/notifications`, `/help`.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│  Chat · Admin Panel · Notifications · Complaint Form     │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP (FastAPI)
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  RAG Engine  │  │ Notice Agent │  │Complaint Agent│  │
│  │ (rag.py)     │  │(notice_agent)│  │(complaint_    │  │
│  │              │  │              │  │ agent.py)     │  │
│  └──────────────┘  └──────────────┘  └───────┬───────┘  │
│                                              │           │
│  ┌───────────────────┐   ┌──────────────────▼────────┐  │
│  │  Student Telegram │   │    Staff Telegram Bot     │  │
│  │  Bot              │   │    (staff_bot.py)         │  │
│  │  (telegram_bot.py)│   │    Role-based forwarding  │  │
│  └───────────────────┘   └───────────────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│               Supabase (PostgreSQL + pgvector)           │
│                                                          │
│  documents · profiles · chats · messages · notices       │
│  complaints · complaint_votes · user_notifications       │
│  hostels · staff_members · staff_rooms                   │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Vanilla CSS |
| Backend | FastAPI, Python 3.11+ |
| Database & Auth | Supabase (PostgreSQL, pgvector, Auth) |
| AI — Generation | Groq API (Llama 3.3-70B Versatile) |
| AI — Embeddings | Google Gemini (`gemini-embedding-2`, 3072-dim) |
| PDF Processing | pdfplumber, pytesseract (OCR), camelot (tables) |
| Bot Platform | Telegram Bot API (Webhook-based, dual bots) |
| Tunnel (dev) | ngrok |

---

## ⚙️ Local Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/vaddethrishank/CampusMind.git
cd CampusMind
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

> **OCR support (optional):** To process scanned/image-based PDFs, also run:
> ```bash
> pip install pymupdf pytesseract
> ```
> And install the [Tesseract binary](https://github.com/UB-Mannheim/tesseract/wiki). The app runs fine without this.

### 3. Environment Variables
A template is provided — copy it and fill in your keys:

```bash
# Mac/Linux
cp .env.example .env

# Windows
copy .env.example .env
```

Then open `.env` and set each value:

```env
# AI APIs
GROQ_API_KEY=your_groq_api_key           # https://console.groq.com
GOOGLE_API_KEY=your_google_gemini_api_key # https://aistudio.google.com/app/apikey

# Supabase (Settings → API in your Supabase project)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=your_supabase_service_role_key

# Student Telegram Bot — create via @BotFather
TELEGRAM_BOT_TOKEN=your_student_bot_token
TELEGRAM_WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app/api/telegram/webhook

# Staff Telegram Bot — create a second bot via @BotFather
STAFF_BOT_TOKEN=your_staff_bot_token
STAFF_BOT_WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app/api/staff/telegram/webhook
```

### 4. Run the backend
```bash
# From the backend/ directory:
uvicorn main:app --reload
```

### 5. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 6. Expose backend with ngrok (for Telegram webhooks)
```bash
ngrok http 8000
```
Copy the HTTPS URL into `TELEGRAM_WEBHOOK_URL` and `STAFF_BOT_WEBHOOK_URL` in `.env`, then restart the backend.

---

## 🗄️ Database Setup

Run the following SQL files **in order** in your Supabase SQL Editor:

| # | File | Purpose |
|---|---|---|
| 1 | `supabase_setup.sql` | Core tables: `documents`, `profiles`, `chats`, `messages`, hybrid search functions |
| 2 | `notices_migration.sql` | `notices` and `user_notifications` tables |
| 3 | `fix_rls.sql` | Row-level security policies for complaints |
| 4 | `telegram_migration.sql` | Adds `telegram_chat_id` column to profiles |
| 5 | `supabase_migrations/20230704170000_add_hostel_and_staff.sql` | **NEW:** `hostels`, `staff_members`, `staff_rooms` tables; extends `complaints` with `hostel_id` and `room_number`; seeds sample hostels |

---

## 📂 Project Structure

```
CampusMind/
├── backend/
│   ├── main.py              # FastAPI app, all endpoints
│   ├── rag.py               # Hybrid search RAG engine
│   ├── complaint_agent.py   # Agentic complaint classification & routing
│   ├── notice_agent.py      # Agentic notice classification & dispatch
│   ├── pdf_processor.py     # PDF ingestion (text, OCR, tables)
│   ├── telegram_bot.py      # Student Telegram bot
│   ├── staff_bot.py         # Staff Telegram bot
│   ├── ingest.py            # Batch PDF ingestion utility
│   └── requirements.txt     # Python dependencies ← install this
├── frontend/
│   ├── src/
│   │   ├── Chat.jsx          # Main chat + complaint UI
│   │   ├── Admin.jsx         # Admin panel
│   │   ├── Auth.jsx          # Login / signup
│   │   └── index.css         # All styles
│   └── package.json          # Node dependencies
├── supabase_migrations/
│   └── 20230704170000_add_hostel_and_staff.sql  # Hostel & staff tables
├── supabase_setup.sql
├── notices_migration.sql
├── fix_rls.sql
├── telegram_migration.sql
├── .env.example              # Environment variable template ← copy to .env
└── .env                      # Your secrets (not committed to git)
```

---

## 🚀 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | RAG chat with history |
| `GET` | `/api/chats` | List user chat sessions |
| `POST` | `/api/complaint/classify` | Fast AI complaint detection (fire-and-forget) |
| `POST` | `/api/complaint` | Full complaint submission + staff forwarding |
| `GET` | `/api/my-complaints` | Student's complaint history |
| `GET` | `/api/hostels` | **NEW** Hostel list for dropdown |
| `POST` | `/api/admin/upload` | PDF ingestion with agentic notice pipeline |
| `POST` | `/api/admin/notices` | Text notice with auto-dispatch |
| `GET` | `/api/admin/complaints` | All complaints (filterable) |
| `PATCH` | `/api/admin/complaints/{id}/status` | Update complaint status |
| `GET` | `/api/notifications` | User notifications |
| `POST` | `/api/telegram/webhook` | Student bot webhook |
| `POST` | `/api/staff/telegram/webhook` | **NEW** Staff bot webhook |

---

## 🔄 Complaint Flow (End-to-End)

```
1. Student types message in chat
        ↓
2. classify_complaint() — LLM detects complaint, assigns:
   • category (hostel/mess/facility/...)
   • staff_role (electrical/cleaning/mess_manager/watchmen)
   • needs_room (true/false — auto-shown in UI)
        ↓
3. Complaint banner appears in UI
   • Hostel dropdown (always required)
   • Room number input (only if needs_room=true, auto-shown by AI)
        ↓
4. Student submits → backend saves to complaints table
        ↓
5. Staff routing (two-pass):
   Pass 1: role + exact hostel match
   Pass 2: role + any hostel (fallback)
        ↓
6. Staff Telegram bot forwards complaint with Ack/Resolve buttons
        ↓
7. Staff taps button → complaint status updated in DB in real-time
```
