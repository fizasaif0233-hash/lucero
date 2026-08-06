# Jarvis Business Assistant

Personal AI executive assistant for multi-business operations (tequila, private token, restaurant, research, marketing, support).

**Phase 1** — Foundation: auth, chat (streaming + RAG), documents, memory, premium dashboard.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 15, TypeScript, Tailwind, App Router |
| Backend | FastAPI, Python 3.12 |
| Database | Supabase PostgreSQL + pgvector |
| Auth | Supabase Auth |
| AI | OpenRouter |
| RAG | LangChain + Supabase embeddings |
| Storage | Supabase Storage |

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for brand sites, shared RAG, and future widget design.

```
frontend/          Secure Jarvis dashboard (Owner + Wife)
backend/
  app/
    api/           HTTP routers
    services/      Business use cases
    ai/            OpenRouter + Jarvis system prompt
    rag/           Ingest, chunk, embed, retrieve, website crawl
    models/        Pydantic schemas
    database/      Supabase clients & repositories
    core/          Config, brand, DI, security
    utils/         Logging, helpers
  migrations/      SQL schema (pgvector, shared knowledge, RLS)
  scripts/         seed_knowledge.py (Assets + websites → RAG)
Assets/            Confidential business deliverables (seeded into RAG)
```

**Websites**
- `anthonywarrenmckinzy.com` — primary brand (future JS widget host)
- `759inc.blue` — exchange/product knowledge source for RAG

Request flow for chat:

1. Client sends message + conversation id (JWT)
2. Backend verifies Supabase JWT
3. RAG retrieves personal + **shared** knowledge (Assets, websites, uploads)
4. AI streams OpenRouter completion with brand-aware system prompt
5. Messages persisted; SSE streamed to UI

## Quick start

### 1. Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. In **Project Settings → API**, copy URL, anon key, service role key
3. In **Project Settings → API → JWT Settings**, copy the JWT secret
4. Run `backend/migrations/001_initial_schema.sql` in the SQL editor
5. Run `backend/migrations/002_storage_policies.sql` (creates `documents` bucket + policies)
6. Run `backend/migrations/003_shared_knowledge.sql` (shared Assets/website RAG)
7. Sign up two users via the app (`/signup`) as **Owner** and **Wife**
8. Seed knowledge (Assets + both websites):

```bash
cd backend
.\.venv\Scripts\activate
python -m scripts.seed_knowledge
```

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
copy .env.example .env          # fill Supabase + OpenRouter keys
uvicorn app.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Frontend

```bash
cd frontend
npm install
copy .env.local.example .env.local   # same Supabase URL/anon + API URL
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment

See `backend/.env.example` and `frontend/.env.local.example`.

## API (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat` | Stream chat (SSE) |
| POST | `/api/v1/upload` | Upload document → RAG ingest |
| GET | `/api/v1/history` | List conversations / messages |
| GET | `/api/v1/documents` | List uploaded documents |
| DELETE | `/api/v1/conversations/{id}` | Delete conversation |

## Phase 1 roles

- **Owner** / **Wife** — both authenticated users; role stored in `users.role`

## Out of scope (later phases)

WhatsApp, Telegram, voice, marketing/research agents, website widget, social posting, automation.
