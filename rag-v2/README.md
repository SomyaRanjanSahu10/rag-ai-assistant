# 🧠 NovaRAG — Production RAG AI Assistant

A fully-featured, production-ready RAG (Retrieval-Augmented Generation) application with authentication, persistent chat history, hybrid search, and a polished SaaS-quality UI.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                            │
│  Login/Register → Protected App → Sidebar + ChatWindow          │
│  Auth Context · Theme Context · useChat · useDocuments hooks    │
└────────────────────────┬────────────────────────────────────────┘
                         │  JWT Bearer · SSE Streaming
┌────────────────────────▼────────────────────────────────────────┐
│                       FastAPI Backend                            │
│                                                                  │
│  /api/auth/*      JWT login · register · refresh                │
│  /api/upload      Parse → Chunk → Embed → Store                 │
│  /api/documents   List · Delete (user-scoped)                   │
│  /api/chat/*      Sessions · Messages · SSE stream              │
│  /api/health      Status check                                   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                Advanced RAG Pipeline                      │   │
│  │  Query Expansion → Hybrid Search → BM25 Fusion →        │   │
│  │  Similarity Filter → LLM Reranking → Parent Context →   │   │
│  │  Deduplication → Groq Streaming → Source Citations       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ChromaDB (vectors) · SQLite/PostgreSQL (users/chat/docs)       │
│  Rate Limiting · Rotating Logs · Global Error Handlers          │
└─────────────────────────────────────────────────────────────────┘
```

### What's New in v2 vs v1

| Feature | v1 | v2 |
|---------|----|----|
| Authentication | ❌ | ✅ JWT + bcrypt |
| Chat history | ❌ in-memory | ✅ Persistent in SQLite/Postgres |
| Retrieval | Semantic only | ✅ Hybrid (Semantic + BM25) |
| Query expansion | ❌ | ✅ Auto-rephrase with LLM |
| Reranking | ❌ | ✅ LLM-based cross-encoder scoring |
| Parent context | ❌ | ✅ Sibling chunk expansion |
| User isolation | ❌ shared | ✅ Per-user scoped |
| Rate limiting | ❌ | ✅ Per-route sliding window |
| Dark mode | ❌ | ✅ System-aware toggle |
| Session management | ❌ | ✅ Rename, delete, list |
| Error handling | Basic | ✅ Global handlers + structured logs |

---

## ✨ Features

### Backend
- 🔐 **JWT Auth** — access + refresh tokens, bcrypt password hashing
- 📄 **Document Processing** — PDF, DOCX, TXT, images (PNG/JPG/WebP)
- 🔍 **Hybrid Search** — cosine similarity + BM25 keyword scoring fused via RRF
- 🧠 **Query Expansion** — LLM generates variant queries for better recall
- ⚡ **Reranking** — LLM scores each retrieved chunk's relevance (0–10)
- 📖 **Parent Context** — expands retrieved chunks to include neighboring text
- 💬 **Conversation Memory** — last 12 messages injected into each LLM request
- 🗄️ **SQLAlchemy + SQLite/PostgreSQL** — users, sessions, messages, documents
- 🚦 **Rate Limiting** — per-route sliding window (in-memory, Redis-ready)
- 📝 **Structured Logging** — rotating file logs with levels
- 🛡️ **Error Handling** — global exception handlers, consistent JSON errors

### Frontend
- 🔒 **Auth pages** — Login/Register with form validation
- 💬 **ChatGPT-style UI** — streaming tokens, typing animation, auto-scroll
- 📚 **Session management** — create, rename, delete, switch conversations
- 📁 **Document sidebar** — drag-drop upload, progress bars, search, delete
- 🌓 **Dark/Light mode** — system-aware with persistent preference
- 👤 **User menu** — profile dropdown, logout
- ✨ **Markdown rendering** — GFM tables, code blocks with syntax highlighting
- 📌 **Source citations** — relevance-scored source pills per message
- 🔔 **Toast notifications** — success/error feedback

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+  
- Node.js 18+  
- Tesseract OCR (optional, for image/scanned-PDF support)  
- Free [Groq API key](https://console.groq.com)

### 1 — Clone
```bash
git clone <your-repo> docmind
cd docmind
```

### 2 — Backend
```bash
cd backend

# System OCR deps (Ubuntu/Debian)
sudo apt-get install -y tesseract-ocr poppler-utils

# macOS
brew install tesseract poppler

# Python env
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Environment
cp .env.example .env
# → Edit .env: set GROQ_API_KEY and SECRET_KEY

# Run (auto-creates DB tables and vector store on first start)
python app.py
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 3 — Frontend
```bash
cd frontend
cp .env.example .env   # optional, defaults to localhost:8000
npm install
npm run dev
# App: http://localhost:3000
```

### 4 — Docker (full stack)
```bash
# Set required vars
echo "GROQ_API_KEY=gsk_..." >> backend/.env
echo "SECRET_KEY=$(openssl rand -hex 32)" >> backend/.env

docker-compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```

---

## 🔧 Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ | — | Get free at console.groq.com |
| `SECRET_KEY` | ✅ | — | 64-char random string for JWT signing |
| `DATABASE_URL` | | SQLite | SQLite (dev) or `postgresql+asyncpg://...` (prod) |
| `GROQ_MODEL` | | `llama-3.3-70b-versatile` | LLM model |
| `MAX_TOKENS` | | `2048` | Max response tokens |
| `TEMPERATURE` | | `0.1` | LLM temperature (lower = more focused) |
| `MAX_FILE_SIZE_MB` | | `50` | Upload size limit |
| `ALLOWED_ORIGINS` | | localhost ports | CORS origins (comma-separated) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | | `7` | Refresh token TTL |
| `LOG_LEVEL` | | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend URL |

---

## 📁 Project Structure

```
docmind-v2/
├── backend/
│   ├── app.py                       # FastAPI entry point
│   ├── database.py                  # Async SQLAlchemy engine + session
│   ├── models/
│   │   ├── user.py                  # User ORM model
│   │   ├── document.py              # Document ORM model
│   │   └── chat.py                  # ChatSession + ChatMessage models
│   ├── repositories/
│   │   ├── document_repo.py         # Document DB operations
│   │   └── chat_repo.py             # Session + message DB operations
│   ├── routes/
│   │   ├── auth.py                  # Register, login, refresh, /me
│   │   ├── upload.py                # File upload + document management
│   │   ├── chat.py                  # Sessions CRUD + SSE streaming
│   │   └── health.py                # Health check
│   ├── rag/
│   │   ├── retrieval_service.py     # Hybrid search + reranking pipeline
│   │   ├── vectorstore.py           # ChromaDB wrapper (user-scoped)
│   │   └── chunker.py               # Configurable text splitter
│   ├── services/
│   │   ├── groq_service.py          # Groq LLM streaming + prompt building
│   │   └── document_processor.py   # PDF/DOCX/image text extraction
│   ├── middleware/
│   │   ├── auth_deps.py             # get_current_user FastAPI dependency
│   │   └── rate_limit.py            # Sliding window rate limiter
│   ├── utils/
│   │   ├── security.py              # JWT + bcrypt utilities
│   │   ├── logger.py                # Rotating file logging setup
│   │   └── errors.py                # Custom exceptions + global handlers
│   ├── logs/                        # Rotating log files (gitignored)
│   ├── uploads/                     # Uploaded files (gitignored)
│   ├── vectorstore/                 # ChromaDB persistent data (gitignored)
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # Root: router + layout + global state
│   │   ├── main.jsx                 # React DOM entry
│   │   ├── context/
│   │   │   ├── AuthContext.jsx      # User state + login/logout/register
│   │   │   └── ThemeContext.jsx     # Dark/light mode
│   │   ├── hooks/
│   │   │   ├── useChat.js           # Sessions + streaming chat state
│   │   │   └── useDocuments.js      # Document list + upload queue
│   │   ├── services/
│   │   │   └── api.js               # Axios + auto-refresh + SSE helper
│   │   ├── pages/
│   │   │   └── AuthPages.jsx        # Login + Register pages
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.jsx      # Sessions + documents side panel
│   │   │   │   └── Navbar.jsx       # Top bar + theme toggle + user menu
│   │   │   ├── chat/
│   │   │   │   └── ChatWindow.jsx   # Messages + input + source pills
│   │   │   ├── upload/
│   │   │   │   └── UploadZone.jsx   # Drag-drop + progress bars
│   │   │   └── auth/
│   │   │       └── ProtectedRoute.jsx
│   │   └── styles/
│   │       └── globals.css          # Tailwind + design tokens + dark mode
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── nginx.conf
│   ├── .env.example
│   └── Dockerfile
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## 📡 API Reference

### Auth
| Method | Path | Body | Description |
|--------|------|------|-------------|
| `POST` | `/api/auth/register` | `{email, username, password}` | Create account |
| `POST` | `/api/auth/login` | `{email, password}` | Get tokens |
| `POST` | `/api/auth/refresh` | `{refresh_token}` | New access token |
| `GET`  | `/api/auth/me` | — | Current user (auth required) |
| `PUT`  | `/api/auth/me` | `{full_name?, avatar_url?}` | Update profile |

### Documents
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Upload + index a document |
| `GET`  | `/api/documents` | List user's documents |
| `DELETE` | `/api/documents/{id}` | Delete document + chunks |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat/sessions` | Create session |
| `GET`  | `/api/chat/sessions` | List sessions |
| `GET`  | `/api/chat/sessions/{id}` | Session + messages |
| `PUT`  | `/api/chat/sessions/{id}` | Rename session |
| `DELETE` | `/api/chat/sessions/{id}` | Delete session |
| `POST` | `/api/chat/sessions/{id}/stream` | **SSE streaming chat** |

#### SSE stream events
```
data: {"type": "start",  "chunks_found": 5, "sources": [...]}
data: {"type": "token",  "content": "Hello"}
data: {"type": "done",   "sources": [...], "latency_ms": 1240}
data: {"type": "error",  "message": "..."}
```

### Health
```
GET /api/health
→ {"status": "healthy", "chunks_indexed": 342, "groq_configured": true}
```

---

## 🚢 Deployment

### Render (backend)
1. New Web Service → connect repo → set root to `backend/`
2. Build: `pip install -r requirements.txt`
3. Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Add env vars: `GROQ_API_KEY`, `SECRET_KEY`, `DATABASE_URL` (Render Postgres)

### Vercel (frontend)
1. New Project → connect repo → set root to `frontend/`
2. Framework: Vite
3. Add env var: `VITE_API_URL=https://your-backend.onrender.com`

### Railway / Docker VPS
```bash
# Generate a secure secret key
openssl rand -hex 32

# Set in backend/.env then:
docker-compose up -d --build
```

---

## 🔐 Security Notes

- Passwords hashed with bcrypt (12 rounds, ~200ms — intentionally slow)
- JWTs signed with HS256 + configurable `SECRET_KEY` — **change in production**
- CORS restricted to explicit origins — update `ALLOWED_ORIGINS` for prod
- File uploads validated by extension + size (50 MB default)
- Path traversal prevented in all file operations
- Rate limiting on all sensitive routes (auth, upload, chat)
- User isolation: all vector store and DB queries scoped by `user_id`

---

## 🧠 RAG Pipeline Deep-Dive

```
User Question
    │
    ▼ 1. Query Expansion (LLM)
    │   "What is revenue?" → ["What is total revenue?", "Annual sales figures?"]
    │
    ▼ 2. Multi-Query Semantic Search (ChromaDB cosine similarity)
    │   Each query variant → top-K chunks → merge, deduplicate
    │
    ▼ 3. BM25 Keyword Scoring
    │   Classic TF-IDF-style relevance on the same candidate pool
    │
    ▼ 4. Hybrid Fusion (Reciprocal Rank Fusion)
    │   score = 0.65 × semantic + 0.35 × BM25 + RRF position bonus
    │
    ▼ 5. Similarity Threshold
    │   Discard chunks below 0.25 relevance
    │
    ▼ 6. LLM Reranking
    │   Groq rates each chunk 0–10 for query relevance → re-sort
    │
    ▼ 7. Parent Context Expansion
    │   Fetch ±1 neighboring chunk from same document for richer context
    │
    ▼ 8. Groq Streaming (LLaMA 3.3 70B)
    │   System prompt + retrieved context + conversation history → answer
    │
    ▼ 9. Source Citations
        Return filename + relevance scores with every response
```

---

## 📄 License

MIT — free for personal and commercial use.
