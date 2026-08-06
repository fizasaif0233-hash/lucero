-- L.U.C.E.R.O channel identity mapping (WhatsApp / Telegram / etc.)
-- Run in Supabase SQL Editor after 003_automation.sql.

-- ---------------------------------------------------------------------------
-- Maps an external messaging identity (phone / JID / chat id) → app user
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.channel_identities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    channel TEXT NOT NULL CHECK (channel IN (
        'whatsapp', 'telegram', 'slack', 'email', 'other'
    )),
    external_id TEXT NOT NULL,
    display_name TEXT,
    allowed BOOLEAN NOT NULL DEFAULT false,
    is_owner BOOLEAN NOT NULL DEFAULT false,
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (channel, external_id)
);

CREATE INDEX IF NOT EXISTS idx_channel_identities_user_id
    ON public.channel_identities(user_id);
CREATE INDEX IF NOT EXISTS idx_channel_identities_channel
    ON public.channel_identities(channel);
CREATE INDEX IF NOT EXISTS idx_channel_identities_allowed
    ON public.channel_identities(allowed)
    WHERE allowed = true;

-- Optional: touch updated_at on change
CREATE OR REPLACE FUNCTION public.set_channel_identities_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_channel_identities_updated_at
    ON public.channel_identities;
CREATE TRIGGER trg_channel_identities_updated_at
    BEFORE UPDATE ON public.channel_identities
    FOR EACH ROW
    EXECUTE FUNCTION public.set_channel_identities_updated_at();

-- ---------------------------------------------------------------------------
-- Channel gateway heartbeat / status (ZeroClaw sidecar)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.channel_gateway_status (
    id TEXT PRIMARY KEY DEFAULT 'default',
    online BOOLEAN NOT NULL DEFAULT false,
    whatsapp_linked BOOLEAN NOT NULL DEFAULT false,
    last_heartbeat_at TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ,
    last_external_id TEXT,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO public.channel_gateway_status (id)
VALUES ('default')
ON CONFLICT (id) DO NOTHING;

COMMENT ON TABLE public.channel_identities IS
    'Allowlist mapping WhatsApp E.164/JID (and other channels) to L.U.C.E.R.O users';
COMMENT ON COLUMN public.channel_identities.external_id IS
    'E.164 phone (+15551234567), WhatsApp JID, or Telegram user id';
COMMENT ON COLUMN public.channel_identities.is_owner IS
    'Owner numbers use full multi-agent router; others default to Support Agent';
