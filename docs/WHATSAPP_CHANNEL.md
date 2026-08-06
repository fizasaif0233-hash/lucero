# WhatsApp Web end-to-end checklist (L.U.C.E.R.O + ZeroClaw)

## Automated (no QR)

```powershell
# Backend must be running on :8000 with ENABLE_CHANNEL_BRIDGE=true
.\scripts\verify-channel-bridge.ps1
```

This hits `GET /v1/models` and `POST /v1/chat/completions` so the OpenAI-compat brain path is proven (RAG/agents when a default/owner user exists).

Deny path:

```powershell
.\scripts\verify-channel-bridge.ps1 -ExpectDeny
```

## WhatsApp QR (requires Rust)

Rust is **not** installed on this machine yet. Install from https://rustup.rs/ then:

1. Apply `backend/migrations/004_channel_identities.sql` in Supabase.
2. Set `CHANNEL_DEFAULT_USER_ID` to Owner `users.id`. For a single WhatsApp sender, set `CHANNEL_ALLOWED_NUMBERS=+923303923361` (comma-separated E.164). ZeroClaw also gates via `peer_groups` / `dm_policy = allowlist` in `config.lucero.toml`.
3. Ensure backend is up with matching `LUCERO_CHANNEL_API_KEY`.
4. Run `.\scripts\start-zeroclaw.ps1` (builds `--features whatsapp-web`, copies `config.lucero.toml`).
5. Scan QR: WhatsApp → Settings → Linked Devices.
6. Send: “Which document contains …?” — expect Document Name + Section citations from L.U.C.E.R.O.

## Status

| Step | Status |
|------|--------|
| OpenAI `/v1` bridge | Implemented + smoke-tested (`verify-channel-bridge.ps1`) |
| Allowlist migration + Channels UI | Implemented (`/dashboard/channels`) |
| ZeroClaw vendor + Lucero config + start script | Implemented |
| Bridge agent reply | Verified (L.U.C.E.R.O reply via `/v1/chat/completions`) |
| Deny unknown numbers | Verified |
| Live QR pair on this host | Needs Rust (`rustup.rs`) then `.\scripts\start-zeroclaw.ps1` |

**Before WhatsApp QR:** run `004_channel_identities.sql` in Supabase, restart backend on `:8000` with the updated code, then install Rust and start ZeroClaw.
