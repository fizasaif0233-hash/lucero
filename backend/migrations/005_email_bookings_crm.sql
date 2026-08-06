-- L.U.C.E.R.O Email, tasting bookings, CRM, reminders
-- Run in Supabase SQL Editor after 003_automation.sql

-- ---------------------------------------------------------------------------
-- Customers (CRM)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    notes TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customers_user_id ON public.customers(user_id);
CREATE INDEX IF NOT EXISTS idx_customers_email ON public.customers(user_id, email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_user_email_unique
    ON public.customers(user_id, lower(email))
    WHERE email IS NOT NULL AND email <> '';

-- ---------------------------------------------------------------------------
-- Extend bookings for tasting + CRM link (keep existing columns)
-- ---------------------------------------------------------------------------
ALTER TABLE public.bookings
    ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES public.customers(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS customer_name TEXT,
    ADD COLUMN IF NOT EXISTS customer_email TEXT,
    ADD COLUMN IF NOT EXISTS phone TEXT,
    ADD COLUMN IF NOT EXISTS notes TEXT,
    ADD COLUMN IF NOT EXISTS guest_count INTEGER DEFAULT 1;

-- Expand status values (drop old check, add new)
ALTER TABLE public.bookings DROP CONSTRAINT IF EXISTS bookings_status_check;
ALTER TABLE public.bookings
    ADD CONSTRAINT bookings_status_check
    CHECK (status IN (
        'draft', 'pending', 'confirmed', 'completed', 'cancelled'
    ));

CREATE INDEX IF NOT EXISTS idx_bookings_customer_id ON public.bookings(customer_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON public.bookings(status);

-- ---------------------------------------------------------------------------
-- Email templates
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.email_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_html TEXT NOT NULL DEFAULT '',
    body_text TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'general',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_templates_user_id
    ON public.email_templates(user_id);

-- ---------------------------------------------------------------------------
-- Emails (drafts + sent)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES public.customers(id) ON DELETE SET NULL,
    booking_id UUID REFERENCES public.bookings(id) ON DELETE SET NULL,
    template_id UUID REFERENCES public.email_templates(id) ON DELETE SET NULL,
    recipient TEXT NOT NULL,
    recipient_name TEXT,
    subject TEXT NOT NULL,
    body_html TEXT NOT NULL DEFAULT '',
    body_text TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN (
            'draft', 'pending_approval', 'approved', 'sending',
            'sent', 'failed', 'cancelled'
        )),
    provider TEXT NOT NULL DEFAULT 'resend',
    message_id TEXT,
    error_message TEXT,
    attachment_meta JSONB NOT NULL DEFAULT '[]'::jsonb,
    folder TEXT NOT NULL DEFAULT 'drafts'
        CHECK (folder IN ('inbox', 'drafts', 'sent', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_emails_user_id ON public.emails(user_id);
CREATE INDEX IF NOT EXISTS idx_emails_status ON public.emails(status);
CREATE INDEX IF NOT EXISTS idx_emails_folder ON public.emails(user_id, folder);
CREATE INDEX IF NOT EXISTS idx_emails_created_at ON public.emails(created_at DESC);

-- ---------------------------------------------------------------------------
-- Email logs (every attempt)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    email_id UUID REFERENCES public.emails(id) ON DELETE SET NULL,
    event TEXT NOT NULL,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_logs_user_id ON public.email_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_email_id ON public.email_logs(email_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_created_at ON public.email_logs(created_at DESC);

-- ---------------------------------------------------------------------------
-- CRM email history + activity timeline
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.crm_email_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES public.customers(id) ON DELETE SET NULL,
    email_id UUID REFERENCES public.emails(id) ON DELETE SET NULL,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    status TEXT NOT NULL,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crm_email_history_user
    ON public.crm_email_history(user_id);
CREATE INDEX IF NOT EXISTS idx_crm_email_history_customer
    ON public.crm_email_history(customer_id);

CREATE TABLE IF NOT EXISTS public.crm_activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES public.customers(id) ON DELETE CASCADE,
    booking_id UUID REFERENCES public.bookings(id) ON DELETE SET NULL,
    email_id UUID REFERENCES public.emails(id) ON DELETE SET NULL,
    activity_type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crm_activities_customer
    ON public.crm_activities(customer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crm_activities_user
    ON public.crm_activities(user_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- Reminders
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    booking_id UUID NOT NULL REFERENCES public.bookings(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('24h', '1h')),
    scheduled_time TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'sent', 'failed', 'cancelled')),
    email_id UUID REFERENCES public.emails(id) ON DELETE SET NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_reminders_due
    ON public.reminders(status, scheduled_time)
    WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_reminders_booking
    ON public.reminders(booking_id);

-- updated_at triggers
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'set_updated_at') THEN
        DROP TRIGGER IF EXISTS trg_customers_updated ON public.customers;
        CREATE TRIGGER trg_customers_updated
            BEFORE UPDATE ON public.customers
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();

        DROP TRIGGER IF EXISTS trg_email_templates_updated ON public.email_templates;
        CREATE TRIGGER trg_email_templates_updated
            BEFORE UPDATE ON public.email_templates
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();

        DROP TRIGGER IF EXISTS trg_emails_updated ON public.emails;
        CREATE TRIGGER trg_emails_updated
            BEFORE UPDATE ON public.emails
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
END $$;

-- RLS
ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.email_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.email_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crm_email_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crm_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reminders ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS customers_owner ON public.customers;
CREATE POLICY customers_owner ON public.customers
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS email_templates_owner ON public.email_templates;
CREATE POLICY email_templates_owner ON public.email_templates
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS emails_owner ON public.emails;
CREATE POLICY emails_owner ON public.emails
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS email_logs_owner ON public.email_logs;
CREATE POLICY email_logs_owner ON public.email_logs
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS crm_email_history_owner ON public.crm_email_history;
CREATE POLICY crm_email_history_owner ON public.crm_email_history
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS crm_activities_owner ON public.crm_activities;
CREATE POLICY crm_activities_owner ON public.crm_activities
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS reminders_owner ON public.reminders;
CREATE POLICY reminders_owner ON public.reminders
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Seed default templates (per-user created on first use in app; skip global seed)
