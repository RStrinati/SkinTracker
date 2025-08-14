-- Daily Mood/Feeling Ratings Migration
-- Add this to Supabase SQL Editor to create the daily_mood_logs table

-- Daily mood logs table to track daily skin feeling ratings from reminders
CREATE TABLE IF NOT EXISTS daily_mood_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mood_rating INTEGER NOT NULL CHECK (mood_rating >= 1 AND mood_rating <= 5),
    mood_description TEXT NOT NULL, -- 'Excellent', 'Good', 'Okay', 'Bad', 'Flare-up'
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_daily_mood_logs_user_id ON daily_mood_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_mood_logs_logged_at ON daily_mood_logs(logged_at);
CREATE INDEX IF NOT EXISTS idx_daily_mood_logs_mood_rating ON daily_mood_logs(mood_rating);

-- Enable Row Level Security (RLS)
ALTER TABLE daily_mood_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for daily_mood_logs table
CREATE POLICY "Users can view own mood logs" ON daily_mood_logs
    FOR SELECT USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can insert own mood logs" ON daily_mood_logs
    FOR INSERT WITH CHECK (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can update own mood logs" ON daily_mood_logs
    FOR UPDATE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can delete own mood logs" ON daily_mood_logs
    FOR DELETE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

-- Add trigger to update updated_at timestamp
CREATE TRIGGER update_daily_mood_logs_updated_at BEFORE UPDATE ON daily_mood_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE daily_mood_logs IS 'Daily skin feeling/mood ratings from reminder responses';
COMMENT ON COLUMN daily_mood_logs.mood_rating IS 'Rating from 1 (Flare-up) to 5 (Excellent)';
COMMENT ON COLUMN daily_mood_logs.mood_description IS 'Text description: Excellent, Good, Okay, Bad, or Flare-up';
