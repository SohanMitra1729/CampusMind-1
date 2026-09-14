# CampusMind 🎓

> **The AI-powered campus assistant for universities** — combining a hybrid RAG knowledge engine, persistent student memory, agentic complaint routing, dual Telegram bots, and a continuous self-learning admin dashboard into one platform.

<div align="center">

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Supabase](https://img.shields.io/badge/Supabase-pgvector-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036?style=for-the-badge)](https://console.groq.com)
[![Gemini](https://img.shields.io/badge/Google-Gemini_Embeddings-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com)

</div>

---

## ✨ What CampusMind Does

CampusMind is a fully autonomous campus intelligence platform. Students chat naturally in a beautiful dark-mode web UI (or via Telegram), and CampusMind:

- **Answers questions** using a hybrid RAG engine over your institution's uploaded PDFs, circulars, and notices
- **Remembers students** across sessions — branch, year, hostel, room, mess, career goals, and more
- **Files and routes complaints** conversationally, with AI assigning the right staff role automatically
- **Broadcasts notices** with targeted delivery to students mentioned in the document
- **Learns from gaps** — when the AI can't answer, the question is logged and shown to admins for 1-click FAQ ingestion into the knowledge base

---

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         React Frontend (Vite)                             │
│   Chat Interface  ·  Admin Portal  ·  Notifications  ·  Complaint Form    │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ HTTPS (SSE Streaming)
┌────────────────────────────────▼─────────────────────────────────────────┐
│                        FastAPI Backend                                    │
│                                                                           │
│  ┌─────────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │  RAG Engine          │  │  Notice Agent     │  │  Complaint Agent   │  │
│  │  • Hybrid Search     │  │  • Auto-classify  │  │  • LLM Detection   │  │
│  │  • RRF Ranking       │  │  • Scholar ID ext │  │  • Staff Routing   │  │
│  │  • Anti-hallucinate  │  │  • Telegram push  │  │  • Dialogue Agent  │  │
│  └─────────────────────┘  └──────────────────┘  └────────────────────┘  │
│                                                                           │
│  ┌─────────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │  Memory Service      │  │  Knowledge Gaps   │  │  Multi-Key Pool    │  │
│  │  • Profile Memory    │  │  • Query Cluster  │  │  • Gemini Failover │  │
│  │  • Conversation Comp │  │  • 1-Click Ingest │  │  • Groq Failover   │  │
│  └─────────────────────┘  └──────────────────┘  └────────────────────┘  │
│                                                                           │
│  ┌───────────────────────────┐    ┌───────────────────────────────────┐  │
│  │  Student Telegram Bot      │    │  Staff Telegram Bot               │  │
│  │  • Account linking         │    │  • Self-registration              │  │
│  │  • Chat / Complaints       │    │  • Instant complaint forwarding   │  │
│  │  • Notifications           │    │  • Inline Ack / Resolve buttons   │  │
│  └───────────────────────────┘    └───────────────────────────────────┘  │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────────┐
│                 Supabase (PostgreSQL + pgvector + Auth)                   │
│                                                                           │
│  documents (HNSW + FTS) · profiles (preferences JSONB) · chats/messages  │
│  complaints · complaint_votes · notices · user_notifications              │
│  hostels · staff_members · bot_sessions · knowledge_gaps                 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Core Feature Modules

### 🤖 Hybrid RAG Engine (`rag_service.py`)
The knowledge retrieval pipeline at the heart of CampusMind:

| Component | Detail |
|---|---|
| **Embeddings** | Google `gemini-embedding-2` — 1536-dim vectors |
| **Search** | PostgreSQL `hybrid_search` RPC: semantic pgvector + full-text `tsvector` |
| **Ranking** | Reciprocal Rank Fusion (RRF) — combines both search modalities |
| **Deduplication** | Character-set fingerprinting removes near-identical PDF chunks |
| **Score Threshold** | `MIN_SCORE = 0.018` — low-confidence chunks are filtered |
| **Anti-Hallucination** | Strict LLM grounding rules — directory-only PDFs cannot fabricate procedures |
| **Fallback Detection** | Unicode-normalized phrase matching triggers knowledge gap logging automatically |
| **Streaming** | Server-Sent Events (SSE) for real-time token streaming to the chat UI |

### 🧠 Persistent Student Memory (`memory_service.py`)
CampusMind remembers students across all conversations — zero repeated questions:

**Automatically extracted & persisted to `profiles.preferences` (JSONB):**
- `program` — B.Tech, M.Tech, MCA, Ph.D, B.Arch, M.Sc, Dual Degree
- `branch` — CSE, ECE, Mechanical, Civil, Electrical, EIE, Chemical
- `academic_year` — 1st through 4th year, semester
- `section` — Section A–D, Group/Batch 1–8
- `resident_type` — Hosteler or Day Scholar
- `hostel` — BH-1 to BH-9, GH-1 to GH-3, PG Hostel
- `room_number` — Room no. extracted from chat
- `mess_preference` — Mess name from conversation
- `career_focus` — GATE, CAT, placement, higher studies, research
- `campus_roles` — CR, NSS, club coordinator
- `financial_category` — Scholarship / fee category

**Rolling Conversation Compression:** Conversations longer than 6 turns are summarized with Groq Llama-3.1-8B to maintain context without blowing token budgets.

### 💡 Continuous Learning: Knowledge Gaps (`knowledge_gap_repository.py`)
When the AI can't answer a question, it doesn't just give up:

1. The question is detected by `_is_unanswered_fallback()` (handles Unicode apostrophes: `'` ≡ `'`)
2. Keywords are extracted (stop-words removed, plurals normalized) and compared via **Jaccard similarity + containment scoring**
3. Semantically identical questions from different students are **clustered into one card** (e.g. *"do we have a swimming pool?"* + *"is swimming pool available on campus?"* → single pending entry, `🔥 Asked 2x`)
4. Alternate phrasings are shown in the Admin Insights tab
5. Admin writes the official answer → clicks **Approve & Vectorize** → it's embedded by Gemini and indexed into pgvector permanently
6. **From that moment**, every student who asks receives the correct, grounded answer

### 📝 AI-Agentic Complaint System (`complaint_agent.py`, `complaint_dialogue_agent.py`)
Complaints are handled entirely through natural chat — no separate form required:

**Detection & Classification (`complaint_agent.py`):**
- Groq Llama classifies message as complaint or regular query (`confidence >= 0.6` threshold)
- Assigns: `category` · `staff_role` · `scope` · `needs_room` · `duplicate_of_id`
- JSON extracted with robust `{[\s\S]*}` regex — handles partial LLM outputs gracefully

**Dialogue Agent (`complaint_dialogue_agent.py`):**
- Multi-turn conversational intake inside the chat interface
- Fuzzy hostel name matching against the live database
- Room number field is auto-requested only when `needs_room=True`
- Duplicate detection: similar open complaints surfaced for upvote instead of re-filing

**Staff Routing (two-pass):**
1. `staff_role` + exact hostel match
2. `staff_role` + any hostel (fallback — no complaint goes unnoticed)

**Staff Telegram Bot (`staff_bot.py`):**
- Self-registration via `/start` — phone, hostel, role — no admin setup needed
- Supported roles: `electrical` · `cleaning` · `mess_manager` · `watchmen`
- Inline buttons: **✅ Acknowledged** / **✔️ Resolved** update the DB in real-time
- `/mystatus` command for staff to check their registration

### 📢 Agentic Notice Pipeline (`notice_agent.py`, `notice_service.py`)
When an admin uploads a PDF or writes a notice:
1. Groq auto-classifies it (general / scholarship / academic / hostel / results / internship)
2. Scholar IDs are extracted from the document via regex
3. Targeted `user_notifications` are created for each mentioned student
4. Telegram push is sent to all linked students instantly
5. The PDF is chunked, embedded by Gemini, and stored in pgvector for RAG retrieval

**PDF processor supports:** text PDFs · scanned/image PDFs (Tesseract OCR) · table-heavy PDFs (camelot)

### 🔑 Multi-Key API Failover Pool (`key_pool.py`)
Zero-downtime operation across multiple API keys:
- **`GeminiKeyPool`** — automatic rotate-on-429/401/403 for embedding generation (sync + async)
- **`GroqKeyPool`** — rotate-on-429/rate-limit for completions (sync, async streaming)
- Supports comma-separated lists of keys in `.env` for pooling across free-tier accounts

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, Vanilla CSS (dark glassmorphic design) |
| **Backend** | FastAPI, Python 3.11+, Uvicorn (ASGI) |
| **Database & Auth** | Supabase (PostgreSQL + pgvector + GoTrue Auth) |
| **AI — Generation** | Groq API (Llama 3.3-70B Versatile) |
| **AI — Embeddings** | Google Gemini (`gemini-embedding-2`, 1536-dim) |
| **Vector Index** | HNSW (pgvector) + GIN (FTS) — in PostgreSQL |
| **PDF Processing** | pdfplumber · pytesseract (OCR) · camelot (tables) |
| **Bots** | Telegram Bot API — dual webhook bots (student + staff) |
| **Deployment** | Render (`render.yaml` included) |
| **Dev Tunnel** | ngrok (for Telegram webhooks during local dev) |

---

## 📂 Project Structure

```
CampusMind/
├── backend/
│   ├── main.py                        # FastAPI app entry point, CORS, router registration
│   ├── requirements.txt
│   └── app/
│       ├── core/
│       │   ├── config.py              # Settings (env vars, multi-key parsing)
│       │   ├── key_pool.py            # 🔑 Multi-key Gemini + Groq failover pools
│       │   └── logger.py
│       ├── db/
│       │   └── supabase.py            # Supabase client singleton
│       ├── repositories/
│       │   ├── chat_repository.py
│       │   ├── complaint_repository.py
│       │   ├── document_repository.py # hybrid_search RPC wrapper
│       │   ├── knowledge_gap_repository.py  # 💡 Gap clustering + Supabase sync
│       │   ├── notice_repository.py
│       │   └── user_repository.py     # 🧠 Profile memory (preferences JSONB)
│       ├── routers/
│       │   ├── auth.py
│       │   ├── chat.py                # /api/chat/stream (SSE) endpoint
│       │   ├── complaints.py
│       │   ├── notices.py             # Admin upload, broadcast, ingestion
│       │   └── webhooks.py
│       ├── schemas/
│       ├── services/
│       │   ├── auth_service.py
│       │   ├── chat_service.py
│       │   ├── complaint_agent.py     # LLM complaint detection + staff assignment
│       │   ├── complaint_dialogue_agent.py  # Multi-turn conversational intake
│       │   ├── complaint_service.py
│       │   ├── memory_service.py      # 🧠 Profile extraction + conversation compression
│       │   ├── notice_agent.py        # Agentic notice classification + Scholar ID extraction
│       │   ├── notice_service.py
│       │   ├── pdf_processor.py       # PDF text / OCR / table ingestion
│       │   ├── rag_service.py         # 🤖 Hybrid RAG engine (core)
│       │   ├── staff_bot.py           # Staff Telegram bot
│       │   └── telegram_bot.py        # Student Telegram bot
│
├── frontend/
│   └── src/
│       ├── App.jsx                    # Router
│       ├── pages/
│       │   ├── ChatPage.jsx           # Main student chat page
│       │   ├── AdminPage.jsx          # Admin portal (tabbed)
│       │   ├── AuthPage.jsx
│       │   └── AdminLoginPage.jsx
│       ├── components/
│       │   ├── chat/
│       │   │   ├── MessageList.jsx    # Chat bubbles with markdown + source citations
│       │   │   ├── ComplaintBanner.jsx
│       │   │   ├── NotificationDrawer.jsx
│       │   │   ├── MyComplaintsModal.jsx
│       │   │   └── Sidebar.jsx        # Chat session history
│       │   ├── admin/
│       │   │   ├── DocumentIngestion.jsx  # PDF upload + vectorize tab
│       │   │   ├── NoticeBroadcast.jsx    # Notice authoring + dispatch
│       │   │   ├── ComplaintManagement.jsx
│       │   │   └── KnowledgeInsights.jsx  # 💡 Gaps dashboard with 1-click FAQ ingest
│       │   └── ui/                    # Button, Dialog, shared primitives
│       ├── hooks/
│       ├── api/
│       └── styles/
│           └── admin.css              # Glassmorphic dark design system
│
├── .env.example                       # ← Copy to .env and fill in your keys
├── render.yaml                        # Render deployment config (backend)
└── .gitignore
```

---

## ⚙️ Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- A [Supabase](https://supabase.com) project (free tier is fine)
- [Groq API key](https://console.groq.com) (free)
- [Google AI Studio API key](https://aistudio.google.com/app/apikey) (free)
- [ngrok](https://ngrok.com) (only needed for Telegram webhooks)

---

### 1. Clone the Repository
```bash
git clone https://github.com/SohanMitra1729/CampusMind-1.git
cd CampusMind-1
```

### 2. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

> **Optional — OCR Support** (for scanned PDFs):
> ```bash
> pip install pymupdf pytesseract
> ```
> Also install the [Tesseract binary](https://github.com/UB-Mannheim/tesseract/wiki). The app runs fine without this for text-based PDFs.

### 3. Environment Variables
```bash
# Mac/Linux
cp .env.example .env

# Windows
copy .env.example .env
```

Edit `.env` and fill in all values:

```env
# ── AI APIs ────────────────────────────────────────────────────────────────────
GROQ_API_KEY=gsk_...           # https://console.groq.com — supports comma-separated list
GOOGLE_API_KEY=AIza...         # https://aistudio.google.com — supports comma-separated list

# ── Supabase ───────────────────────────────────────────────────────────────────
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...    # Service Role key (Settings → API)

# ── Admin Panel ────────────────────────────────────────────────────────────────
ADMIN_USERNAME=admin
ADMIN_SECRET=change_me_to_a_strong_random_secret   # openssl rand -hex 32

# ── Frontend CORS ──────────────────────────────────────────────────────────────
FRONTEND_URL=http://localhost:5173

# ── Student Telegram Bot ───────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=...
TELEGRAM_WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app/api/telegram/webhook

# ── Staff Telegram Bot ─────────────────────────────────────────────────────────
STAFF_BOT_TOKEN=...
STAFF_BOT_WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app/api/staff/telegram/webhook
```

> **Multi-key tip:** Both `GROQ_API_KEY` and `GOOGLE_API_KEY` support comma-separated values for pooling across multiple free-tier accounts — e.g., `GROQ_API_KEY=key1,key2,key3`

### 4. Database Setup (Supabase SQL Editor)
Run the following SQL in your Supabase **SQL Editor** in one shot:

```sql
-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Core tables: documents, profiles (with preferences), chats, messages
-- knowledge_gaps, bot_sessions, complaints, notices, notifications,
-- hostels, staff_members, and hybrid search function
-- → See the complete schema in schema_complete.sql (run locally, not committed to git)
```

> The complete production schema is in `schema_complete.sql` (not committed to Git — migrations are managed locally). Key tables:
>
> | Table | Purpose |
> |---|---|
> | `documents` | pgvector + FTS — all embedded institutional knowledge |
> | `profiles` | Student accounts with `preferences JSONB` for memory |
> | `chats` / `messages` | Persistent conversation history |
> | `knowledge_gaps` | Unanswered query tracking (RLS disabled — backend only) |
> | `bot_sessions` | Telegram + chat state machine storage |
> | `complaints` | Full complaint lifecycle |
> | `notices` / `user_notifications` | Notice broadcast + per-student delivery |
> | `hostels` / `staff_members` | Ground-truth hostel directory + staff registry |

### 5. Run the Backend
```bash
# From the backend/ directory (with venv active):
uvicorn main:app --reload
# Runs at http://localhost:8000
```

### 6. Run the Frontend
```bash
cd frontend
npm install
npm run dev
# Runs at http://localhost:5173
```

### 7. Enable Telegram Webhooks (Optional)
```bash
ngrok http 8000
```
Copy the HTTPS URL into `TELEGRAM_WEBHOOK_URL` and `STAFF_BOT_WEBHOOK_URL` in `.env`, then restart the backend. Webhooks register automatically on startup.

---

## 🚀 API Reference

### Chat
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat/stream` | SSE streaming RAG chat (JWT-authenticated) |
| `GET` | `/api/chats` | List user's chat sessions |
| `GET` | `/api/chats/{id}/messages` | Fetch message history |
| `DELETE` | `/api/chats/{id}` | Delete a chat session |

### Complaints
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/complaint/classify` | Fast LLM classification check |
| `POST` | `/api/complaint` | Submit complaint + trigger staff routing |
| `GET` | `/api/my-complaints` | Student's own complaint history |
| `GET` | `/api/hostels` | Hostel list for dropdown |

### Notifications
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/notifications` | User's notification inbox |
| `PATCH` | `/api/notifications/{id}/read` | Mark as read |
| `POST` | `/api/notifications/mark-all-read` | Mark all read |

### Admin Portal (Bearer token required)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/admin/auth` | Admin login |
| `POST` | `/api/admin/upload` | PDF upload + embed + notice pipeline |
| `POST` | `/api/admin/notices` | Broadcast text notice |
| `GET` | `/api/admin/complaints` | All complaints (filterable by status/hostel) |
| `PATCH` | `/api/admin/complaints/{id}/status` | Update complaint status |
| `GET` | `/api/admin/knowledge-gaps` | Unanswered questions for review |
| `POST` | `/api/admin/knowledge-gaps/{id}/approve` | Vectorize official answer into RAG |
| `DELETE` | `/api/admin/knowledge-gaps/{id}` | Dismiss a knowledge gap |

### Telegram Webhooks
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/telegram/webhook` | Student bot incoming updates |
| `POST` | `/api/staff/telegram/webhook` | Staff bot incoming updates |

---

## 🔄 Key User Flows

### RAG Chat Flow
```
Student sends message
  → POST /api/chat/stream
  → Memory service injects student profile context
  → Compression: if > 6 turns, older history is summarized (Groq Llama-3.1-8B)
  → Gemini embeds query (1536-dim)
  → hybrid_search() → RRF ranking → score threshold → deduplication
  → Top 4 chunks + hostel directory + personal academic record assembled
  → Groq Llama-3.3-70B streams response with anti-hallucination rules
  → _is_unanswered_fallback() checks response
     └── If fallback: log to knowledge_gaps, suppress unrelated source citations
  → Memory service extracts new student facts → updates profiles.preferences
  → SSE tokens stream to React chat UI
```

### Complaint Filing Flow
```
Student describes a problem naturally in the chat
  (e.g. "My room fan is not working" / "Mess food is very bad today")
  ↓
classify_complaint() — LLM detects complaint intent (confidence >= 0.6)
  assigns: category + staff_role + needs_room + scope + duplicate_of_id
  ↓
dialogue_agent replies in chat:
  "Which hostel are you in?" → student replies → fuzzy matched against DB
  "What's your room number?" → only asked if needs_room=True (room-specific issues)
  Hostel-wide issues (mess, corridor, power) skip the room question entirely
  ↓
Bot confirms submission in chat with complaint ID and assigned staff role
  ↓
complaint saved to DB → two-pass staff routing:
  Pass 1: matching role + matching hostel
  Pass 2: matching role + any hostel (fallback — no complaint goes unrouted)
  ↓
Staff Telegram bot forwards complaint → [✅ Ack] [✔️ Resolve] inline buttons
  ↓
Staff taps button → DB status updated instantly → student sees update in chat
```

### Knowledge Gap Self-Learning Flow
```
Student asks question with no institutional answer
  ↓
_is_unanswered_fallback() detects the fallback response
  ↓
log_knowledge_gap():
  • Extract keywords (stop-words removed, plurals normalized)
  • Compare against existing pending gaps via Jaccard + containment score
  • If similar gap exists → cluster (increment frequency, store alternate phrasing)
  • If new → log to knowledge_gaps table + Supabase
  ↓
Admin sees "🔥 Asked 2x" card in Knowledge Insights tab
Also asked as: "is swimming pool available?" + "do we have a pool?"
  ↓
Admin writes official institutional answer
  ↓
Approve & Vectorize → Gemini embeds the FAQ → stored in pgvector documents
  ↓
All future students get the correct grounded answer immediately
```

---

## 🚢 Deployment (Render)

The repository includes `render.yaml` for one-click backend deployment on [Render](https://render.com).

```yaml
services:
  - type: web
    name: campusmind-backend
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn main:app --host 0.0.0.0 --port $PORT"
    rootDir: backend
```

**Steps:**
1. Push your code to GitHub.
2. Go to [render.com](https://render.com) → **New Web Service** → Connect your repo.
3. Render auto-detects `render.yaml`.
4. Add all environment variables from `.env.example` in the Render dashboard.
5. Deploy — Render handles the rest.

**Frontend:** Deploy to [Vercel](https://vercel.com) or [Netlify](https://netlify.com):
- Root: `frontend/`
- Build command: `npm run build`
- Output dir: `dist`
- Add `VITE_API_BASE_URL=https://your-render-backend.onrender.com` as an env variable.

---

## 🔒 Security

| Concern | Implementation |
|---|---|
| **Auth** | Supabase GoTrue JWT — all chat/complaint endpoints require `Authorization: Bearer <token>` |
| **Admin Auth** | Separate `ADMIN_SECRET` Bearer token for all `/api/admin/*` endpoints |
| **Secrets** | `.env` is gitignored — `.env.example` is the only committed template |
| **Data Isolation** | Row-Level Security (RLS) on `profiles`, `chats`, `messages`, `complaints` |
| **knowledge_gaps RLS** | Insert allowed for `anon`/`authenticated`/`service_role`; SELECT blocked for public browser access |
| **CORS** | Strict origin allowlist via `FRONTEND_URL` env var |
| **API Key Safety** | Multi-key pool — individual key compromise doesn't break service |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes and commit: `git commit -m "feat: describe your change"`
4. Push to your fork: `git push origin feature/your-feature-name`
5. Open a Pull Request targeting `main`

---

## 📄 License

This project is licensed under the MIT License.

---

<div align="center">
  <strong>Built for NIT Silchar · Designed for any university</strong><br/>
  <sub>CampusMind — where AI meets campus life</sub>
</div>
