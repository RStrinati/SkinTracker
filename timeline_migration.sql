-- =========================================
-- Timeline Events: indexes + unified view
-- =========================================

-- Create indexes for better timeline query performance (idempotent)
DO $$
DECLARE
  col_exists boolean;
BEGIN
  -- symptom_logs: (user_id, timestamp) since your view uses s.timestamp
  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'ix_symptom_logs_user_time' AND n.nspname = 'public'
  ) THEN
    PERFORM 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'symptom_logs' AND column_name = 'timestamp';
    IF FOUND THEN
      EXECUTE 'CREATE INDEX ix_symptom_logs_user_time ON public.symptom_logs (user_id, "timestamp")';
    ELSE
      -- fallback if your table uses logged_at instead
      EXECUTE 'CREATE INDEX ix_symptom_logs_user_time ON public.symptom_logs (user_id, logged_at)';
    END IF;
  END IF;

  -- product_logs: (user_id, logged_at)
  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'ix_product_logs_user_time' AND n.nspname = 'public'
  ) THEN
    EXECUTE 'CREATE INDEX ix_product_logs_user_time ON public.product_logs (user_id, logged_at)';
  END IF;

  -- trigger_logs: (user_id, logged_at)
  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'ix_trigger_logs_user_time' AND n.nspname = 'public'
  ) THEN
    EXECUTE 'CREATE INDEX ix_trigger_logs_user_time ON public.trigger_logs (user_id, logged_at)';
  END IF;

  -- photo_logs: (user_id, logged_at)
  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'ix_photo_logs_user_time' AND n.nspname = 'public'
  ) THEN
    EXECUTE 'CREATE INDEX ix_photo_logs_user_time ON public.photo_logs (user_id, logged_at)';
  END IF;

  -- skin_kpis: uses "timestamp" (NOT logged_at)
  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'ix_skin_kpis_user_time' AND n.nspname = 'public'
  ) THEN
    EXECUTE 'CREATE INDEX ix_skin_kpis_user_time ON public.skin_kpis (user_id, "timestamp")';
  END IF;

  -- daily_mood_logs: (user_id, logged_at)
  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'ix_mood_logs_user_time' AND n.nspname = 'public'
  ) THEN
    EXECUTE 'CREATE INDEX ix_mood_logs_user_time ON public.daily_mood_logs (user_id, logged_at)';
  END IF;

  -- conditions: (user_id, diagnosed_at)
  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'ix_conditions_user_diag' AND n.nspname = 'public'
  ) THEN
    EXECUTE 'CREATE INDEX ix_conditions_user_diag ON public.conditions (user_id, diagnosed_at)';
  END IF;
END
$$;

-- Unified timeline events view (uses correct per-table timestamp columns)
CREATE OR REPLACE VIEW public.vw_timeline_events AS
-- 1) Symptoms
SELECT
  s.id,
  s.user_id,
  'Symptoms'::text                 AS lane,
  s.symptom_name                   AS title,
  s."logged_at"                    AS start_ts,
  NULL::timestamptz                AS end_ts,
  s.severity                       AS severity,
  ARRAY[LOWER(s.symptom_name)]::text[] AS tags,
  NULL::text                       AS media_url,
  NULLIF(s.notes, '')              AS details,
  CAST('user' AS text)             AS source
FROM public.symptom_logs s

UNION ALL

-- 2) Products
SELECT
  p.id,
  p.user_id,
  'Products'::text                 AS lane,
  p.product_name                   AS title,
  p.logged_at                      AS start_ts,
  NULL::timestamptz                AS end_ts,
  NULL::integer                    AS severity,
  CASE WHEN p.effect IS NOT NULL THEN ARRAY[LOWER(p.effect)]::text[] ELSE ARRAY[]::text[] END AS tags,
  NULL::text                       AS media_url,
  NULLIF(p.notes, '')              AS details,
  CAST('user' AS text)             AS source
FROM public.product_logs p

UNION ALL

-- 3) Triggers
SELECT
  t.id,
  t.user_id,
  'Triggers'::text                 AS lane,
  t.trigger_name                   AS title,
  t.logged_at                      AS start_ts,
  NULL::timestamptz                AS end_ts,
  NULL::integer                    AS severity,
  ARRAY[]::text[]                  AS tags,
  NULL::text                       AS media_url,
  NULLIF(t.notes, '')              AS details,
  CAST('user' AS text)             AS source
FROM public.trigger_logs t

UNION ALL

-- 4) Photos
SELECT
  ph.id,
  ph.user_id,
  'Photos'::text                   AS lane,
  'Photo'::text                    AS title,
  ph.logged_at                     AS start_ts,
  NULL::timestamptz                AS end_ts,
  NULL::integer                    AS severity,
  ARRAY[]::text[]                  AS tags,
  ph.photo_url                     AS media_url,
  NULLIF(ph.ai_analysis, '')       AS details,
  CAST('user' AS text)             AS source
FROM public.photo_logs ph

UNION ALL

-- 5) Skin KPIs (automated)
SELECT
  k.id,
  k.user_id,
  'Symptoms'::text                 AS lane,
  'Blemish %'::text                AS title,
  k."timestamp"                    AS start_ts,
  NULL::timestamptz                AS end_ts,
  NULL::integer                    AS severity,
  ARRAY['kpi','blemish_pct']::text[] AS tags,
  k.blemish_image_path             AS media_url,
  NULL::text                       AS details,
  CAST('bot' AS text)              AS source
FROM public.skin_kpis k

UNION ALL

-- 6) Daily mood
SELECT
  m.id,
  m.user_id,
  'Notes'::text                    AS lane,
  ('Mood: ' || m.mood_rating::text)::text AS title,
  m.logged_at                      AS start_ts,
  NULL::timestamptz                AS end_ts,
  NULL::integer                    AS severity,
  ARRAY['mood']::text[]            AS tags,
  NULL::text                       AS media_url,
  NULLIF(m.mood_description, '')   AS details,
  CAST('user' AS text)             AS source
FROM public.daily_mood_logs m

UNION ALL

-- 7) Diagnoses
SELECT
  c.id,
  c.user_id,
  'Notes'::text                    AS lane,
  ('Diagnosis: ' || c.name)::text  AS title,
  c.diagnosed_at                   AS start_ts,
  NULL::timestamptz                AS end_ts,
  NULL::integer                    AS severity,
  CASE
    WHEN c.condition_type IS NOT NULL
      THEN ARRAY['diagnosis', LOWER(c.condition_type)]::text[]
    ELSE ARRAY['diagnosis']::text[]
  END                             AS tags,
  NULL::text                       AS media_url,
  NULLIF(c.notes, '')              AS details,
  CAST('user' AS text)             AS source
FROM public.conditions c
WHERE c.diagnosed_at IS NOT NULL;


-- Helper index for common query pattern (by user/time on symptoms)
CREATE INDEX IF NOT EXISTS ix_vw_timeline_events_user_time 
ON public.symptom_logs (user_id, "logged_at");

-- Docs
COMMENT ON VIEW public.vw_timeline_events IS 'Unified timeline view consolidating all user events for visualization';
COMMENT ON COLUMN public.vw_timeline_events.lane IS 'Event category: Symptoms, Products, Triggers, Photos, Notes';
COMMENT ON COLUMN public.vw_timeline_events.severity IS 'Severity rating 1-5 (only for symptoms)';
COMMENT ON COLUMN public.vw_timeline_events.tags IS 'Searchable tags for filtering';
COMMENT ON COLUMN public.vw_timeline_events.source IS 'Event origin: user or bot';
