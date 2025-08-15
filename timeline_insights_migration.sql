CREATE OR REPLACE FUNCTION public.get_trigger_insights(
  p_user_id       uuid,
  p_window_hours  integer DEFAULT 24,
  p_since         timestamptz DEFAULT NULL,
  p_until         timestamptz DEFAULT NULL,
  p_min_pairs     integer DEFAULT 2
)
RETURNS TABLE (
  trigger_name text,
  symptom_name text,
  pair_count   integer,
  trig_count   integer,
  sym_count    integer,
  confidence   numeric,  -- P(symptom within window | trigger)
  baseline     numeric,  -- symptom share of all events
  lift         numeric   -- confidence / baseline
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  WITH t AS (
    SELECT tl.user_id, tl.trigger_name, tl.logged_at
    FROM public.trigger_logs tl
    WHERE tl.user_id = p_user_id
      AND (p_since IS NULL OR tl.logged_at >= p_since)
      AND (p_until IS NULL OR tl.logged_at <  p_until)
  ),
  s AS (
    SELECT sl.user_id, sl.symptom_name, sl.severity, sl."timestamp" AS ts
    FROM public.symptom_logs sl
    WHERE sl.user_id = p_user_id
      AND (p_since IS NULL OR sl."timestamp" >= p_since)
      AND (p_until IS NULL OR sl."timestamp" <  p_until)
  ),
  pairs AS (
    SELECT
      t.user_id,
      t.trigger_name,
      s.symptom_name,
      COUNT(*)::int                        AS pair_count
    FROM t
    JOIN s
      ON s.user_id = t.user_id
     AND s.ts >= t.logged_at
     AND s.ts <  t.logged_at + make_interval(hours => p_window_hours)
    GROUP BY 1,2,3
  ),
  t_counts AS (
    SELECT user_id, trigger_name, COUNT(*)::int AS trig_count
    FROM t
    GROUP BY 1,2
  ),
  s_counts AS (
    SELECT user_id, symptom_name, COUNT(*)::int AS sym_count
    FROM s
    GROUP BY 1,2
  ),
  totals AS (
    SELECT user_id, COUNT(*)::int AS total_events
    FROM (
      SELECT user_id FROM t
      UNION ALL
      SELECT user_id FROM s
    ) u
    GROUP BY 1
  )
  SELECT
    p.trigger_name,
    p.symptom_name,
    p.pair_count,
    tc.trig_count,
    sc.sym_count,
    (p.pair_count::numeric / NULLIF(tc.trig_count, 0))                                           AS confidence,
    (sc.sym_count::numeric / NULLIF(tot.total_events, 0))                                         AS baseline,
    (p.pair_count::numeric / NULLIF(tc.trig_count, 0))
    / NULLIF((sc.sym_count::numeric / NULLIF(tot.total_events, 0)), 0)                            AS lift
  FROM pairs p
  JOIN t_counts tc ON tc.user_id = p.user_id AND tc.trigger_name = p.trigger_name
  JOIN s_counts sc ON sc.user_id = p.user_id AND sc.symptom_name = p.symptom_name
  JOIN totals   tot ON tot.user_id = p.user_id
  WHERE p.pair_count >= p_min_pairs
  ORDER BY lift DESC NULLS LAST, confidence DESC NULLS LAST;
END;
$$;
