-- =========================================
-- Re-run-safe schema updates for UX features
-- =========================================

-- --- Utility: updated_at trigger function (safe to re-run)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

-- --- Columns (idempotent)
ALTER TABLE users          ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE symptom_logs   ADD COLUMN IF NOT EXISTS area TEXT;
ALTER TABLE photo_logs     ADD COLUMN IF NOT EXISTS area TEXT;

-- --- Tables (idempotent with column fixes)
CREATE TABLE IF NOT EXISTS user_areas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- Fix daily_mood_logs table - add missing columns if they don't exist
CREATE TABLE IF NOT EXISTS daily_mood_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "timestamp" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add missing columns to daily_mood_logs if they don't exist
ALTER TABLE daily_mood_logs ADD COLUMN IF NOT EXISTS rating INTEGER CHECK (rating >= 1 AND rating <= 5);
ALTER TABLE daily_mood_logs ADD COLUMN IF NOT EXISTS mood_description TEXT;
ALTER TABLE daily_mood_logs ADD COLUMN IF NOT EXISTS notes TEXT;

-- Update the constraint to allow NULL initially, then add NOT NULL after data migration if needed
-- This prevents issues with existing incomplete records
DO $$
BEGIN
    -- Drop existing constraint if it exists and recreate
    ALTER TABLE daily_mood_logs DROP CONSTRAINT IF EXISTS daily_mood_logs_rating_check;
    ALTER TABLE daily_mood_logs ADD CONSTRAINT daily_mood_logs_rating_check 
        CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5));
EXCEPTION
    WHEN others THEN
        -- Constraint might not exist, continue
        NULL;
END $$;

CREATE TABLE IF NOT EXISTS skin_kpis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    photo_id UUID REFERENCES photo_logs(id) ON DELETE CASCADE,
    face_area_px INTEGER,
    blemish_area_px INTEGER,
    percent_blemished REAL,
    "timestamp" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- --- Indexes (idempotent)
CREATE INDEX IF NOT EXISTS idx_user_areas_user_id       ON user_areas(user_id);
CREATE INDEX IF NOT EXISTS idx_user_areas_name          ON user_areas(name);

CREATE INDEX IF NOT EXISTS idx_daily_mood_logs_user_id  ON daily_mood_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_mood_logs_logged_at ON daily_mood_logs(logged_at);

CREATE INDEX IF NOT EXISTS idx_skin_kpis_user_id        ON skin_kpis(user_id);
CREATE INDEX IF NOT EXISTS idx_skin_kpis_timestamp      ON skin_kpis("timestamp");

CREATE INDEX IF NOT EXISTS idx_symptom_logs_area        ON symptom_logs(area);
CREATE INDEX IF NOT EXISTS idx_photo_logs_area          ON photo_logs(area);

-- --- RLS enable (idempotent)
ALTER TABLE user_areas      ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_mood_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE skin_kpis       ENABLE ROW LEVEL SECURITY;

-- =========================================
-- Policies: drop-if-exists then create
-- =========================================

-- user_areas
DROP POLICY IF EXISTS "Users can view own areas"   ON user_areas;
DROP POLICY IF EXISTS "Users can insert own areas" ON user_areas;
DROP POLICY IF EXISTS "Users can update own areas" ON user_areas;
DROP POLICY IF EXISTS "Users can delete own areas" ON user_areas;

CREATE POLICY "Users can view own areas" ON user_areas
  FOR SELECT USING (
    user_id IN (
      SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    )
  );

CREATE POLICY "Users can insert own areas" ON user_areas
  FOR INSERT WITH CHECK (
    user_id IN (
      SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    )
  );

CREATE POLICY "Users can update own areas" ON user_areas
  FOR UPDATE USING (
    user_id IN (
      SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    )
  );

CREATE POLICY "Users can delete own areas" ON user_areas
  FOR DELETE USING (
    user_id IN (
      SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    )
  );

-- daily_mood_logs
DROP POLICY IF EXISTS "Users can view own mood logs"   ON daily_mood_logs;
DROP POLICY IF EXISTS "Users can insert own mood logs" ON daily_mood_logs;
DROP POLICY IF EXISTS "Users can update own mood logs" ON daily_mood_logs;
DROP POLICY IF EXISTS "Users can delete own mood logs" ON daily_mood_logs;

CREATE POLICY "Users can view own mood logs" ON daily_mood_logs
  FOR SELECT USING (
    user_id IN (
      SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    )
  );

CREATE POLICY "Users can insert own mood logs" ON daily_mood_logs
  FOR INSERT WITH CHECK (
    user_id IN (
      SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    )
  );

CREATE POLICY "Users can update own mood logs" ON daily_mood_logs
  FOR UPDATE USING (
    user_id IN (
      SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    )
  );

CREATE POLICY "Users can delete own mood logs" ON daily_mood_logs
  FOR DELETE USING (
    user_id IN (
      SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    )
  );

-- skin_kpis
DROP POLICY IF EXISTS "Users can view own skin kpis"   ON skin_kpis;
DROP POLICY IF EXISTS "Users can insert own skin kpis" ON skin_kpis;
DROP POLICY IF EXISTS "Users can update own skin kpis" ON skin_kpis;
DROP POLICY IF EXISTS "Users can delete own skin kpis" ON skin_kpis;

CREATE POLICY "Users can view own skin kpis" ON skin_kpis
  FOR SELECT USING (
    user_id IN (
      SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    )
  );

CREATE POLICY "Users can insert own skin kpis" ON skin_kpis
  FOR INSERT WITH CHECK (
    user_id IN (
      SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    )
  );

CREATE POLICY "Users can update own skin kpis" ON skin_kpis
  FOR UPDATE USING (
    user_id IN (
      SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    )
  );

CREATE POLICY "Users can delete own skin kpis" ON skin_kpis
  FOR DELETE USING (
    user_id IN (
      SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    )
  );

-- =========================================
-- Triggers: drop-if-exists then create
-- =========================================
DROP TRIGGER IF EXISTS update_user_areas_updated_at      ON user_areas;
DROP TRIGGER IF EXISTS update_daily_mood_logs_updated_at ON daily_mood_logs;
DROP TRIGGER IF EXISTS update_skin_kpis_updated_at       ON skin_kpis;

CREATE TRIGGER update_user_areas_updated_at
  BEFORE UPDATE ON user_areas
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_mood_logs_updated_at
  BEFORE UPDATE ON daily_mood_logs
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_skin_kpis_updated_at
  BEFORE UPDATE ON skin_kpis
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================================
-- Documentation comments (idempotent)
-- =========================================
COMMENT ON TABLE user_areas IS 'User-defined areas for focused skin tracking';
COMMENT ON TABLE daily_mood_logs IS 'Daily skin condition ratings and mood tracking';
COMMENT ON TABLE skin_kpis IS 'AI-analyzed skin metrics from photos';

-- Only add comments if columns exist
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'daily_mood_logs' AND column_name = 'rating') THEN
        COMMENT ON COLUMN daily_mood_logs.rating IS 'Daily skin condition rating from 1 (very bad) to 5 (excellent)';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'skin_kpis' AND column_name = 'percent_blemished') THEN
        COMMENT ON COLUMN skin_kpis.percent_blemished IS 'Percentage of face area affected by blemishes';
    END IF;
END $$;
