-- L.U.C.E.R.O AI Operating System — jobs, assets, task audit
-- Run in Supabase SQL Editor after 005_email_bookings_crm.sql

CREATE TABLE IF NOT EXISTS public.ai_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE SET NULL,
    client_request_id TEXT,
    task_type TEXT NOT NULL,
    pipeline JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
    progress INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    progress_detail TEXT,
    input JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ai_jobs_user_id ON public.ai_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_jobs_status ON public.ai_jobs(status, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_jobs_client_request
    ON public.ai_jobs(user_id, client_request_id)
    WHERE client_request_id IS NOT NULL AND client_request_id <> '';

CREATE TABLE IF NOT EXISTS public.generated_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES public.ai_jobs(id) ON DELETE SET NULL,
    kind TEXT NOT NULL
        CHECK (kind IN ('image', 'video', 'docx', 'pdf', 'audio', 'json', 'markdown', 'other')),
    title TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    public_url TEXT,
    mime TEXT NOT NULL DEFAULT 'application/octet-stream',
    byte_size INTEGER,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_generated_assets_user
    ON public.generated_assets(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_assets_job
    ON public.generated_assets(job_id);
CREATE INDEX IF NOT EXISTS idx_generated_assets_kind
    ON public.generated_assets(user_id, kind);

CREATE TABLE IF NOT EXISTS public.os_task_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE SET NULL,
    prompt TEXT NOT NULL,
    plan JSONB NOT NULL DEFAULT '{}'::jsonb,
    model TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_os_task_runs_user
    ON public.os_task_runs(user_id, created_at DESC);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'set_updated_at') THEN
        DROP TRIGGER IF EXISTS trg_ai_jobs_updated ON public.ai_jobs;
        CREATE TRIGGER trg_ai_jobs_updated
            BEFORE UPDATE ON public.ai_jobs
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    END IF;
END $$;

-- Allow service role writes; owners can read their rows via RLS
ALTER TABLE public.ai_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generated_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.os_task_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ai_jobs_owner ON public.ai_jobs;
CREATE POLICY ai_jobs_owner ON public.ai_jobs
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS generated_assets_owner ON public.generated_assets;
CREATE POLICY generated_assets_owner ON public.generated_assets
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS os_task_runs_owner ON public.os_task_runs;
CREATE POLICY os_task_runs_owner ON public.os_task_runs
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Storage bucket for generated OS assets (service role uploads; signed URLs for clients)
INSERT INTO storage.buckets (id, name, public)
VALUES ('generated-assets', 'generated-assets', true)
ON CONFLICT (id) DO UPDATE SET public = EXCLUDED.public;

DROP POLICY IF EXISTS generated_assets_storage_owner ON storage.objects;
CREATE POLICY generated_assets_storage_owner ON storage.objects
    FOR ALL
    USING (
        bucket_id = 'generated-assets'
        AND (
            auth.role() = 'service_role'
            OR auth.uid()::text = (storage.foldername(name))[1]
        )
    )
    WITH CHECK (
        bucket_id = 'generated-assets'
        AND (
            auth.role() = 'service_role'
            OR auth.uid()::text = (storage.foldername(name))[1]
        )
    );

-- public_url column for older installs that already created generated_assets
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'generated_assets'
          AND column_name = 'public_url'
    ) THEN
        ALTER TABLE public.generated_assets ADD COLUMN public_url TEXT;
    END IF;
END $$;
