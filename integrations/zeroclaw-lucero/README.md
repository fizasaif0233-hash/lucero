# ZeroClaw ↔ L.U.C.E.R.O (WhatsApp / channels)

ZeroClaw is the **transport sidecar** (WhatsApp Web, Telegram, …).
L.U.C.E.R.O FastAPI is the **brain** (RAG + specialist agents) via an OpenAI-compatible bridge.

```
WhatsApp → ZeroClaw → POST http://127.0.0.1:8000/v1/chat/completions → Agents + RAG → reply
```

Upstream ZeroClaw source lives in this folder (`Cargo.toml`, `docs/`). Lucero-specific files:

| File | Purpose |
|------|---------|
| `config.lucero.toml` | Points ZeroClaw at L.U.C.E.R.O `/v1` |
| `README.LUCERO.md` | This guide |

A durable copy of the Lucero overlay also lives in `../zeroclaw-lucero/` so re-clones can restore it.

## Prerequisites (Windows)

1. **Rust** toolchain: https://rustup.rs/ (`rustc --version`)
2. **L.U.C.E.R.O backend** running on port 8000 with:
   - `ENABLE_CHANNEL_BRIDGE=true`
   - `LUCERO_CHANNEL_API_KEY=...` (same value as ZeroClaw)
   - `CHANNEL_DEFAULT_USER_ID=<your Supabase users.id>` (Owner)
3. Apply `backend/migrations/004_channel_identities.sql` in Supabase
4. Allowlist phones on Dashboard → Channels

## Build (WhatsApp Web)

```powershell
cd integrations\zeroclaw
cargo build --release --features whatsapp-web
```

## Configure & start

From the repo root:

```powershell
$env:LUCERO_CHANNEL_API_KEY = "lucero-dev-channel-key-change-in-prod"
.\scripts\start-zeroclaw.ps1
```

The script copies `config.lucero.toml` → `%USERPROFILE%\.zeroclaw\config.toml` and runs `zeroclaw channel start`.

## QR pairing

1. Start ZeroClaw; terminal shows QR (or pair code).
2. Phone: **WhatsApp → Settings → Linked Devices → Link a Device**.
3. Scan once; message an allowlisted number.
4. Reply should use L.U.C.E.R.O RAG / Support Agent (owners get full multi-agent router).

## Verify the brain without WhatsApp

```powershell
curl.exe -s -X POST http://127.0.0.1:8000/v1/chat/completions `
  -H "Authorization: Bearer lucero-dev-channel-key-change-in-prod" `
  -H "Content-Type: application/json" `
  -H "X-Lucero-External-Id: +15551234567" `
  -d "{\"model\":\"lucero/agents\",\"messages\":[{\"role\":\"user\",\"content\":\"Ping from channel bridge\"}]}"
```

## Telegram later

Enable `[channels_config.telegram]` in the ZeroClaw config — same `/v1` brain, no FastAPI changes.
