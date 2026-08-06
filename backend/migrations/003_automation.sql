-- L.U.C.E.R.O Automation Mode schema
-- Run in Supabase SQL Editor.

-- ---------------------------------------------------------------------------
-- Automation runs (one user request → draft → approve → execute)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.automation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    module TEXT NOT NULL CHECK (module IN (
        'email', 'calendar', 'marketing', 'research',
        'report', 'support', 'crm'
    )),
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planning'
        CHECK (status IN (
            'planning', 'draft_ready', 'awaiting_approval',
            'approved', 'executed', 'cancelled', 'failed'
        )),
    plan_summary TEXT,
    preview JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_automation_runs_user_id
    ON public.automation_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_automation_runs_module
    ON public.automation_runs(module);
CREATE INDEX IF NOT EXISTS idx_automation_runs_status
    ON public.automation_runs(status);
CREATE INDEX IF NOT EXISTS idx_automation_runs_created_at
    ON public.automation_runs(created_at DESC);

-- ---------------------------------------------------------------------------
-- Draft items inside a run (emails, posts, bookings, etc.)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.automation_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES public.automation_runs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    item_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'edited', 'approved', 'rejected', 'executed')),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_automation_items_run_id
    ON public.automation_items(run_id);

-- ---------------------------------------------------------------------------
-- Calendar bookings (confirmed after approval)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.bookings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    run_id UUID REFERENCES public.automation_runs(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ,
    location TEXT,
    guests JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'confirmed'
        CHECK (status IN ('draft', 'confirmed', 'cancelled')),
    external_calendar_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON public.bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_starts_at ON public.bookings(starts_at);

-- ---------------------------------------------------------------------------
-- Marketing library assets
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.marketing_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    run_id UUID REFERENCES public.automation_runs(id) ON DELETE SET NULL,
    channel TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketing_assets_user_id
    ON public.marketing_assets(user_id);

-- ---------------------------------------------------------------------------
-- Research / executive reports
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.automation_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    run_id UUID REFERENCES public.automation_runs(id) ON DELETE SET NULL,
    report_type TEXT NOT NULL,
    title TEXT NOT NULL,
    markdown TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_automation_reports_user_id
    ON public.automation_reports(user_id);

-- updated_at trigger reuse if function exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'set_updated_at'
    ) THEN
        DROP TRIGGER IF EXISTS trg_automation_runs_updated ON public.automation_runs;
        CREATE TRIGGER trg_automation_runs_updated
            BEFORE UPDATE ON public.automation_runs
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();

        DROP TRIGGER IF EXISTS trg_automation_items_updated ON public.automation_items;
        CREATE TRIGGER trg_automation_items_updated
            BEFORE UPDATE ON public.automation_items
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();

        DROP TRIGGER IF EXISTS trg_bookings_updated ON public.bookings;
        CREATE TRIGGER trg_bookings_updated
            BEFORE UPDATE ON public.bookings
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
END $$;

ALTER TABLE public.automation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.automation_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.marketing_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.automation_reports ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS; owner policies for future client access
DROP POLICY IF EXISTS automation_runs_owner ON public.automation_runs;
CREATE POLICY automation_runs_owner ON public.automation_runs
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS automation_items_owner ON public.automation_items;
CREATE POLICY automation_items_owner ON public.automation_items
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS bookings_owner ON public.bookings;
CREATE POLICY bookings_owner ON public.bookings
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS marketing_assets_owner ON public.marketing_assets;
CREATE POLICY marketing_assets_owner ON public.marketing_assets
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS automation_reports_owner ON public.automation_reports;
CREATE POLICY automation_reports_owner ON public.automation_reports
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
