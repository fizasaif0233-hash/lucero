# ZeroClaw ↔ L.U.C.E.R.O (WhatsApp / channels)

ZeroClaw is the **transport sidecar** (WhatsApp Web).
L.U.C.E.R.O FastAPI is the **brain** (RAG + specialist agents) via an OpenAI-compatible bridge.

```
Customer → Client WhatsApp → ZeroClaw → POST …/v1/chat/completions → Agents + RAG → reply
```

## Production (24/7)

Build & run the Docker image in this folder (see `Dockerfile`, `docker-compose.yml`, `railway.toml`).

- Brain URI: `https://lucero-api-production.up.railway.app/v1`
- Volume: `/zeroclaw-data` (persists Linked Devices session)
- Env: `LUCERO_CHANNEL_API_KEY`, `ZEROCLAW_PAIR_PHONE`

Full checklist: [`docs/WHATSAPP_CHANNEL.md`](../../docs/WHATSAPP_CHANNEL.md)

## Local (Windows)

1. Rust: https://rustup.rs/
2. Lucero API with `ENABLE_CHANNEL_BRIDGE=true` and matching `LUCERO_CHANNEL_API_KEY`
3. From repo root:

```powershell
$env:LUCERO_CHANNEL_API_KEY = "..."
$env:ZEROCLAW_PAIR_PHONE = "+923203628978"
.\scripts\start-zeroclaw.ps1
```

Config template: `config.lucero.toml` (copied into `~/.zeroclaw/config.toml`).

## Reply mode

Default: **all customers** who DM the linked business WhatsApp.
Leave Lucero `CHANNEL_ALLOWED_NUMBERS` empty. Optional Dashboard → Channels identities map Owner phones to full agents.
