# Jarvis Architecture — Brand & Knowledge

## Product shape

```
Anthony (Owner) + Wife
        │
        ▼
Jarvis Dashboard (Next.js)  ← secure app
        │
        ▼
FastAPI Backend
        ├── Task Router (chat / knowledge / research / marketing / personal)
        ├── OpenRouter AI
        ├── RAG Knowledge Base (shared + personal)
        ├── Research Agent (Assets-first + optional web search)
        ├── Supabase (Auth, Postgres, pgvector, Storage)
        └── Conversation + Business Memory
```

## Two modes

### 1. Knowledge Mode (Phase 1 — primary)

Answers from uploaded Assets, website knowledge, CRM, financial model, pitch deck, memory.
Works offline relative to live web APIs (except the LLM).

Examples: “What is my token?”, “Who are my Dubai distributors?”, “Explain my financial model.”

### 2. Agent Mode (Phase 2 — Research Agent live)

Task Router detects research intents (“find investors”, “research distributors”).
Flow:

```
User → Task Router → Research Agent
  → search Assets/RAG
  → optional web search
  → progress SSE events
  → ranked report via Jarvis
```

Later: Marketing Agent, Automation Agent (WhatsApp/Telegram/CRM) plug into the same router.

## Websites

| Site | Role |
|------|------|
| **https://www.anthonywarrenmckinzy.com** | Primary brand site. Jarvis is designed around this brand. Future public chat widget embeds here with a JS snippet only. |
| **https://www.759inc.blue** | Business knowledge source (Private Exchange, tokens, product info). Indexed into RAG — not the app shell. |

Jarvis Phase 1 is a **separate secure web app**. It does not live inside either WordPress/static site.

## Knowledge sources (RAG)

1. Local `Assets/` deliverables (pitch, playbooks, CRM exports, calendars, etc.)
2. Crawled pages from anthonywarrenmckinzy.com
3. Crawled pages from 759inc.blue
4. Manual uploads (PDF, TXT, DOCX, CSV, XLSX)

Shared sources use `is_shared=true` so both Owner and Wife retrieve them.

### Seed command

```bash
cd backend
.\.venv\Scripts\activate
# Apply migrations/003_shared_knowledge.sql in Supabase first
# Sign up Owner once in the UI
python -m scripts.seed_knowledge
```

## Future website widget (not built yet)

Target embed for anthonywarrenmckinzy.com:

```html
<script
  src="https://jarvis.yourdomain.com/widget.js"
  data-api="https://api.yourdomain.com"
  data-site="anthonywarrenmckinzy.com"
  async
></script>
```

Architecture already prepared:

- CORS allows the primary brand domain
- Chat/RAG stay in FastAPI services (widget will call the same APIs)
- Public widget auth can be a site key / anonymous session layer later without changing RAG or OpenRouter internals
- No need to fork the backend for embed support

## Roadmap modules

| Phase | Module | Status |
|-------|--------|--------|
| 1 | Chat, RAG, memory, voice, HUD | Built |
| 1.5 / 2 | Task router + Research Agent (Assets + web) | Built |
| 2 | Automation Mode (draft → approve → execute) | Built |
| 2 | Specialist AI Agents + Agent Router | Built — marketing, investor, distributor, document, finance, support |
| 2b | ZeroClaw channel sidecar (WhatsApp Web) | Built — OpenAI `/v1` bridge + Channels UI; QR via `start-zeroclaw.ps1` |
| 3 | Live providers (Gmail/SendGrid, Google Calendar, outbound WA/Telegram) | Stubs ready; inbound WhatsApp via ZeroClaw |

AI Agents UI: `/dashboard/agents`  
Add new agents in `backend/app/agents/registry.py` — router discovers them automatically.

Toggle web research: `ENABLE_WEB_RESEARCH=true` in backend `.env`.
Optional reliable web search: set `SERPER_API_KEY` (https://serper.dev). If unset, DuckDuckGo is tried and L.U.C.E.R.O still answers from Assets when web is rate-limited.

## Channel agents (ZeroClaw WhatsApp)

```
WhatsApp User → ZeroClaw Gateway → POST /v1/chat/completions → L.U.C.E.R.O Agents + RAG → reply
```

- **Transport:** ZeroClaw sidecar (`integrations/zeroclaw`, overlay in `integrations/zeroclaw-lucero/`)
- **Brain:** FastAPI OpenAI-compatible bridge (`backend/app/api/openai_compat.py`) — not ZeroClaw’s own OpenRouter brain
- **Auth:** `Authorization: Bearer <LUCERO_CHANNEL_API_KEY>` with `ENABLE_CHANNEL_BRIDGE=true`
- **Identity:** `channel_identities` (`migrations/004_channel_identities.sql`) maps WhatsApp E.164 → user; owners get full Agent Router, others default to Support Agent
- **UI:** `/dashboard/channels` — bridge status, allowlist, QR pairing instructions
- **Start:** `.\scripts\start-zeroclaw.ps1` (Rust + `cargo build --release --features whatsapp-web`)
- **Config template:** `integrations/zeroclaw/config.lucero.toml` → `default_provider = "custom:http://127.0.0.1:8000/v1"`

Telegram / Slack later reuse the same `/v1` bridge (config-only on ZeroClaw).

