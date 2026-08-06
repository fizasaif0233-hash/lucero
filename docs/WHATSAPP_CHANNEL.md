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
| `LUCERO_API_BASE` | Default `https://lucero-api-production.up.railway.app` |
| `ZEROCLAW_PAIR_PHONE` | Optional. Leave empty for QR on Lucero Channels. Set digits-only for pair-code mode. |

### Persistent volume

Mount Railway volume at `/zeroclaw-data` so the Linked Devices session survives redeploys.

### Pair once (client scans QR in Lucero)

1. Keep `lucero-whatsapp` running on Railway.
2. Client opens **https://lucero-zeta.vercel.app/dashboard/channels** on a **computer**.
3. A scannable QR appears on that page (relayed from the WhatsApp sidecar — not Railway logs).
4. On the **business phone**: WhatsApp → Settings → Linked Devices → Link a device → scan that QR.
5. Customers message that business number — Lucero replies.

Do **not** scan the QR in Railway Deploy Logs (that view breaks it).

Fallback: `.\scripts\pair-whatsapp-then-upload.ps1` then `-UploadOnly`.

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
