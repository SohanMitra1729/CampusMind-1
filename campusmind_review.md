# CampusMind — Full Project Review

> **Verdict at a glance**: Solid first-pass for a college internship, especially the RAG + hybrid search design is genuinely good. But the codebase is a *flat script dump* right now — everything lives in one layer with no separation of concerns. A targeted restructure (not a full rewrite) will make it production-ready and much easier to maintain.

---

## 1 · What you built (and what's actually good)

| Feature | Verdict |
|---|---|
| Hybrid search (RRF, pgvector + FTS) | ✅ Excellent — this is real engineering |
| 3-stage agentic notice pipeline (classify → extract → notify) | ✅ Smart token-budget design |
| Complaint pipeline with similar-complaint deduplication | ✅ Good product thinking |
| Telegram student + staff bots | ✅ Works, clean intent |
| React + Vite frontend | ✅ Modern stack choice |
| Supabase RLS policies | ✅ Correct approach |
| Per-student personal record pinning in RAG | ✅ Clever shortcut |

---

## 2 · Critical Issues (Fix Before Anything Else)

### 🔴 `main.py` is a 775-line God File
Everything — auth, chat, documents, complaints, notices, notifications, admin, webhooks — lives in one file. This is the single biggest structural problem. It kills testability, readability, and collaboration.

### 🔴 Zero Authentication / Authorization on Sensitive Endpoints
```python
# Anyone can call these — no token verification at all:
@app.get("/api/admin/complaints")
@app.patch("/api/admin/complaints/{complaint_id}/status")
@app.post("/api/admin/upload")
@app.delete("/api/admin/documents/{filename}")
```
The "admin auth" is just a `sessionStorage` flag on the frontend — trivially bypassable. The backend has **no auth middleware at all**. Every admin endpoint is publicly callable with curl.

### 🔴 User ID Passed in Request Body (Not from Token)
```python
@app.get("/api/chats")
async def get_chats(user_id: str):   # 🔴 client tells you who they are!
```
Any user can pass any `user_id` and read another user's chats. This is a classic IDOR (Insecure Direct Object Reference). The `user_id` must come from a verified JWT, not the request body.

### 🔴 `CORS allow_origins=["*"]` in Production
This is fine locally but you should lock this to your actual frontend domain when deployed. On Render you have a real domain.

### 🔴 Blocking `time.sleep()` in an Async Endpoint
```python
# In the /api/admin/upload endpoint — this blocks the entire event loop!
time.sleep(SLEEP_SECS)  # 7 seconds × N batches
```
FastAPI is async. `time.sleep()` here freezes the whole server. Use `await asyncio.sleep()` or run the embedding loop in a `BackgroundTask`.

### 🔴 In-Memory Bot State Is Not Production-Safe
```python
_bot_state: dict = {}  # in telegram_bot.py
```
This state is per-process and dies on every restart. On Render (single instance) it "works", but it's a hidden footgun. Use a DB row or Redis for real conversation state.

---

## 3 · Architecture Issues

### 🟡 No Separation of Concerns (No Layering)
Your current structure vs the target you drew:

```
Current (flat):                 Target (layered):
backend/
  main.py         (775 lines)   routers/auth.py, chat.py, ...
  rag.py          (supabase + groq + logic mixed)
  complaint_agent.py            services/complaint_service.py
  notice_agent.py               services/notice_service.py
  telegram_bot.py               services/rag_service.py
  staff_bot.py                  repositories/chat_repository.py
  pdf_processor.py              ...
```

`rag.py` initializes a global Supabase client **and** contains business logic. Every other file just imports that global. This makes unit testing impossible and creates implicit coupling.

### 🟡 Circular-Adjacent Imports
`complaint_agent.py` does `from staff_bot import send_complaint_to_staff` inside a function body (to avoid circular imports). This is a code smell — it means your modules are too tightly coupled. The correct fix is dependency injection: pass `send_complaint_to_staff` as a callback, or use a service layer.

### 🟡 Config Is Scattered
`load_dotenv(dotenv_path="../.env")` appears in **at least 4 different files** (`rag.py`, `complaint_agent.py`, `notice_agent.py`, `staff_bot.py`, `telegram_bot.py`). There should be one `config.py` that owns all settings.

### 🟡 No Dependency Injection
The `supabase` client is passed as a function argument in some places and used as a global import in others. FastAPI has a built-in `Depends()` mechanism that's the standard way to handle this cleanly.

### 🟡 Supabase Client Created Multiple Times
`rag.py` creates one client. If you ever add other modules they'd create another. Use a singleton pattern or FastAPI's `lifespan` context to create it once.

---

## 4 · Code Quality Issues

### 🟡 No Input Validation / Sanitization on Several Endpoints
```python
@app.delete("/api/admin/documents/{filename}")
async def delete_document(filename: str):
    supabase.table("documents").delete().like("metadata->source", f"%{filename}%")
```
`filename` is user-controlled and goes directly into a LIKE query. Passing `%` or `../../../` as filename could cause unintended behavior.

### 🟡 Vote Count Has a Race Condition
```python
current_count = current.data[0]["vote_count"]
# ← Another request could vote here
supabase.table("complaints").update({"vote_count": current_count + 1})
```
Two concurrent votes could both read `count=5`, both write `6`. Fix: use a PostgreSQL `RPC` or `update votes = votes + 1` (Supabase supports this via SQL RPC).

### 🟡 Inconsistent Error Handling
Some endpoints return `HTTP 400` for DB errors (should be `500`), others return `HTTP 500` for client errors (should be `400`). Auth errors should be `401/403`, not `400`.

### 🟡 `re.match(r"[^@]+@[^@]+\.[^@]+", req.email)` 
You already have `pydantic` and `EmailStr` imported — just use `email: EmailStr` in the model instead of rolling your own regex.

### 🟡 Unused Import
`from pydantic import BaseModel, EmailStr` — `EmailStr` is imported but not used in the actual Pydantic models (email is just `str`).

### 🟡 Magic Numbers
```python
BATCH_SIZE = 10
SLEEP_SECS = 7
MIN_SCORE = 0.005
```
These are scattered inline. Put them in a `config.py` or use `pydantic-settings`.

### 🟡 No Logging — Only `print()`
Every `print(f"[RAG]...")` should be `logger.info(...)` from Python's `logging` module. This gives you log levels, structured output, and lets you silence debug output in production.

---

## 5 · Frontend Issues

### 🟡 All Auth in `localStorage` with Manual Expiry Check
```javascript
if (session.expires_at && session.expires_at > now) { ... }
```
This works but doesn't handle token refresh. If the user's session expires while they're using the app, API calls will silently fail. You need a refresh flow or an interceptor that catches `401` responses.

### 🟡 No API Client Abstraction
Every API call across `Chat.jsx` (30K bytes!), `Admin.jsx` (30K bytes!) is a raw `fetch()` with hardcoded `import.meta.env.VITE_API_URL`. You need a centralized API client (`/src/api/client.js`) that handles base URL, auth headers, and error handling in one place.

### 🟡 Giant Monolith Components
- `Chat.jsx` → 30,267 bytes (~800+ lines)
- `Admin.jsx` → 30,920 bytes (~850+ lines)
- `index.css` → 63,640 bytes (!!!!)

These should be broken into smaller, focused components. The CSS is especially concerning — likely has duplicated rules and dead styles.

### 🟡 Admin Access Is Just a URL Hash
`/#admin-login` is "security by obscurity." The backend must enforce admin auth independently.

### 🟡 No React Router
Navigation between views is done via state flags and hash changes. For a multi-view app, use `react-router-dom`.

---

## 6 · On Your SQLAlchemy Question

**Short answer: No, don't add SQLAlchemy.**

**Why not:**

1. **You're using Supabase** — Supabase's Python client is your "ORM." It gives you a typed query builder, RLS enforcement, and auth integration. SQLAlchemy would bypass RLS entirely and duplicate the abstraction.

2. **You have pgvector + custom RPCs** — `hybrid_search()` and `match_documents()` are PostgreSQL functions that Supabase's `.rpc()` calls perfectly. SQLAlchemy would make this more complex, not less.

3. **The complexity cost is high** — SQLAlchemy requires models, sessions, migrations (Alembic), connection pools. You already have Supabase managing all that.

4. **What you should do instead** — Create a **Repository layer** that wraps your Supabase calls. This gives you the same testability and abstraction benefit as an ORM without the overhead:

```python
# repositories/chat_repository.py
class ChatRepository:
    def __init__(self, db: Client):
        self.db = db

    def get_chats_by_user(self, user_id: str) -> list[dict]:
        res = self.db.table("chats").select("id, title, created_at").eq("user_id", user_id).order("created_at", desc=True).execute()
        return res.data or []

    def create_chat(self, user_id: str, title: str) -> dict:
        res = self.db.table("chats").insert({"user_id": user_id, "title": title}).execute()
        return res.data[0]
```

---

## 7 · Tech Stack Assessment

| Current | Assessment | Recommendation |
|---|---|---|
| FastAPI | ✅ Perfect choice | Keep |
| Supabase (Postgres + pgvector + Auth) | ✅ Great for this use case | Keep |
| Groq (llama-3.3-70b) | ✅ Fast, cheap inference | Keep |
| Gemini Embeddings | ✅ 3072-dim = high quality | Keep |
| React + Vite | ✅ Good modern choice | Keep |
| Vanilla CSS | ⚠️ 63KB of CSS is too much | Consider CSS Modules or one component library |
| No router | 🔴 Problematic | Add `react-router-dom` |
| No auth middleware | 🔴 Security gap | Add FastAPI dependency for JWT verification |
| No logging | 🟡 Hard to debug in prod | Add Python `logging` |
| No tests | 🔴 Zero coverage | Add at least `pytest` for service logic |

---

## 8 · Recommended Restructuring Plan

### Phase 1 — Security (Do This First, Nothing Else Matters Until Then)
1. Add a FastAPI `Depends(verify_token)` dependency that extracts `user_id` from the Supabase JWT
2. Protect all `/api/admin/*` endpoints with a separate admin-role check
3. Replace all request-body `user_id` parameters with token-derived IDs
4. Fix `asyncio.sleep` in upload endpoint

### Phase 2 — Backend Structure (Matches Your Target Architecture)
```
backend/
  app/
    main.py              # FastAPI app creation + lifespan only
    core/
      config.py          # pydantic-settings, single load_dotenv
      security.py        # JWT verification dependency
      logging.py         # logging config
    db/
      supabase.py        # Singleton Supabase client (via lifespan)
    schemas/             # Pydantic request/response models (move out of main.py)
      auth.py
      chat.py
      complaint.py
      notice.py
    repositories/        # Supabase query wrappers (no business logic)
      chat_repository.py
      complaint_repository.py
      notice_repository.py
      document_repository.py
    services/            # Business logic (uses repositories, agents)
      auth_service.py
      chat_service.py
      rag_service.py     # absorbs rag.py
      complaint_service.py  # absorbs complaint_agent.py
      notice_service.py     # absorbs notice_agent.py
      document_service.py   # absorbs pdf_processor.py
    routers/             # FastAPI route handlers (thin — just call services)
      auth.py
      chat.py
      documents.py
      complaints.py
      notifications.py
      admin.py
      webhooks.py
    agents/              # LLM orchestration (currently in *_agent.py files)
      complaint_agent.py
      notice_agent.py
  scripts/
    ingest.py
  tests/
    test_complaint_service.py
    test_rag_service.py
```

### Phase 3 — Frontend Structure
```
src/
  api/
    client.js            # base fetch wrapper with auth headers
    chatApi.js
    complaintApi.js
    notificationApi.js
  components/
    chat/
      ChatSidebar.jsx
      ChatMessages.jsx
      ChatInput.jsx
      ComplaintModal.jsx
    notifications/
      NotificationBell.jsx
      NotificationList.jsx
    admin/
      DocumentsPanel.jsx
      ComplaintsPanel.jsx
      NoticesPanel.jsx
  pages/
    ChatPage.jsx
    AuthPage.jsx
    AdminPage.jsx
  hooks/
    useAuth.js
    useChat.js
    useNotifications.js
  styles/                # per-component CSS modules
```

---

## 9 · Quick Wins (Low effort, high impact)

1. **Move Pydantic schemas** out of `main.py` into `schemas/` — 30 min, instant readability win
2. **Replace `print()` with `logging`** — 1 hour
3. **Create `core/config.py`** with `pydantic-settings` and remove all the `load_dotenv()` calls — 1 hour
4. **Fix the race condition in `vote_on_complaint`** — use a PostgreSQL RPC with `complaints.vote_count + 1` directly
5. **Use `EmailStr`** in SignUpRequest instead of the manual regex
6. **Add `asyncio.sleep`** in the upload endpoint
7. **Add `.env.example`** to the backend (you have it at root but not backend-specific)
