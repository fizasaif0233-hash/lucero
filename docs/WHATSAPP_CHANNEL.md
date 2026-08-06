# WhatsApp business line — Lucero replies to all customers

## How it works

1. **Client** links **their** WhatsApp once (Linked Devices / pair code) to the Lucero WhatsApp sidecar.
2. **Customers** message that business number in WhatsApp (no QR for them).
3. **Lucero** replies to **every** inbound DM on that line (Support / RAG by default).

```
Customer → Client WhatsApp → ZeroClaw (24/7) → POST /v1/chat/completions → Lucero agents + RAG → reply
```

## Production (24/7 on Railway)

Service: `lucero-whatsapp`  
Image build: [`integrations/zeroclaw-lucero/Dockerfile`](../integrations/zeroclaw-lucero/Dockerfile)  
Brain: `https://lucero-api-production.up.railway.app/v1`

### Required env (WhatsApp service)

| Variable | Purpose |
|----------|---------|
| `LUCERO_CHANNEL_API_KEY` | Same secret as Lucero API |
| `ZEROCLAW_PAIR_PHONE` | Client business WhatsApp E.164 (e.g. `+923203628978`) |
| `LUCERO_API_BASE` | Default `https://lucero-api-production.up.railway.app` |

### Persistent volume

Mount Railway volume at `/zeroclaw-data` so the Linked Devices session survives redeploys.

### Pair once (use pair code — Railway web QR is not scannable)

Railway’s Deploy Logs UI **breaks ASCII QR codes**. Do not try to scan them there.

1. Set `ZEROCLAW_PAIR_PHONE` to the business WhatsApp digits only (e.g. `923203628978`).
2. Restart `lucero-whatsapp`.
3. On your PC run:

```powershell
.\scripts\show-whatsapp-pair.ps1
```

4. Copy the **8-character pair code** from the terminal.
5. On the **business** phone: WhatsApp → Settings → Linked Devices → Link a device → **Link with phone number instead** → enter the code.
6. From any customer phone, message the business number — Lucero should reply.

### Lucero API env (already on `lucero-api`)

| Variable | Value for all-customers mode |
|----------|------------------------------|
| `ENABLE_CHANNEL_BRIDGE` | `true` |
| `LUCERO_CHANNEL_API_KEY` | shared secret |
| `CHANNEL_DEFAULT_USER_ID` | owner `users.id` |
| `CHANNEL_DEFAULT_AGENT` | `support` |
| `CHANNEL_ALLOWED_NUMBERS` | **empty / unset** (reply to all) |

If `CHANNEL_ALLOWED_NUMBERS` is set to a comma-separated list, only those E.164 senders get replies.

## Local (optional)

```powershell
# Backend bridge must be enabled; WhatsApp sidecar points at Railway by default.
$env:LUCERO_CHANNEL_API_KEY = "..."
$env:ZEROCLAW_PAIR_PHONE = "+923203628978"
# Optional: talk to local API instead
# $env:LUCERO_API_BASE = "http://127.0.0.1:8000"
.\scripts\start-zeroclaw.ps1
```

Or Docker Compose from the overlay:

```powershell
cd integrations\zeroclaw-lucero
$env:LUCERO_CHANNEL_API_KEY = "..."
docker compose up -d --build
docker compose logs -f
```

## Verify brain without WhatsApp

```powershell
.\scripts\verify-channel-bridge.ps1
```

Hit production:

```powershell
curl.exe -s -X POST https://lucero-api-production.up.railway.app/v1/chat/completions `
  -H "Authorization: Bearer YOUR_CHANNEL_KEY" `
  -H "Content-Type: application/json" `
  -H "X-Lucero-External-Id: +15551234567" `
  -d "{\"model\":\"lucero/agents\",\"messages\":[{\"role\":\"user\",\"content\":\"Ping from a customer\"}]}"
```

## Dashboard

**Channels** (`/dashboard/channels`): bridge status, pairing instructions, optional named identities (Owner vs Support). Identities are **not** required for every customer when reply mode is all-customers.

## Migration

Apply [`backend/migrations/004_channel_identities.sql`](../backend/migrations/004_channel_identities.sql) in Supabase if not already applied.
