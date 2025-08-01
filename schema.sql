-- Skin Health Tracker Database Schema for Supabase
-- Execute this in Supabase SQL Editor to set up the database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table to store Telegram user information
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Product logs table to track skincare products used
CREATE TABLE IF NOT EXISTS product_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_name TEXT NOT NULL,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trigger logs table to track skin irritation triggers
CREATE TABLE IF NOT EXISTS trigger_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trigger_name TEXT NOT NULL,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Symptom logs table to track skin symptoms with severity ratings
CREATE TABLE IF NOT EXISTS symptom_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symptom_name TEXT NOT NULL,
    severity INTEGER NOT NULL CHECK (severity >= 1 AND severity <= 5),
    notes TEXT,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Photo logs table to store skin photos and AI analysis
CREATE TABLE IF NOT EXISTS photo_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    photo_url TEXT NOT NULL,
    ai_analysis TEXT,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_product_logs_user_id ON product_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_product_logs_logged_at ON product_logs(logged_at);
CREATE INDEX IF NOT EXISTS idx_trigger_logs_user_id ON trigger_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_trigger_logs_logged_at ON trigger_logs(logged_at);
CREATE INDEX IF NOT EXISTS idx_symptom_logs_user_id ON symptom_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_symptom_logs_logged_at ON symptom_logs(logged_at);
CREATE INDEX IF NOT EXISTS idx_photo_logs_user_id ON photo_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_photo_logs_logged_at ON photo_logs(logged_at);

-- Enable Row Level Security (RLS) for all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE trigger_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE symptom_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE photo_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
-- Users can only access their own data
CREATE POLICY "Users can view own data" ON users
    FOR SELECT USING (telegram_id = current_setting('request.telegram_id')::bigint);

CREATE POLICY "Users can update own data" ON users
    FOR UPDATE USING (telegram_id = current_setting('request.telegram_id')::bigint);

CREATE POLICY "Users can insert own data" ON users
    FOR INSERT WITH CHECK (telegram_id = current_setting('request.telegram_id')::bigint);

-- RLS Policies for product_logs table
CREATE POLICY "Users can view own product logs" ON product_logs
    FOR SELECT USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can insert own product logs" ON product_logs
    FOR INSERT WITH CHECK (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can update own product logs" ON product_logs
    FOR UPDATE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can delete own product logs" ON product_logs
    FOR DELETE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

-- RLS Policies for trigger_logs table
CREATE POLICY "Users can view own trigger logs" ON trigger_logs
    FOR SELECT USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can insert own trigger logs" ON trigger_logs
    FOR INSERT WITH CHECK (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can update own trigger logs" ON trigger_logs
    FOR UPDATE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can delete own trigger logs" ON trigger_logs
    FOR DELETE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

-- RLS Policies for symptom_logs table
CREATE POLICY "Users can view own symptom logs" ON symptom_logs
    FOR SELECT USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can insert own symptom logs" ON symptom_logs
    FOR INSERT WITH CHECK (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can update own symptom logs" ON symptom_logs
    FOR UPDATE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can delete own symptom logs" ON symptom_logs
    FOR DELETE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

-- RLS Policies for photo_logs table
CREATE POLICY "Users can view own photo logs" ON photo_logs
    FOR SELECT USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can insert own photo logs" ON photo_logs
    FOR INSERT WITH CHECK (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can update own photo logs" ON photo_logs
    FOR UPDATE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can delete own photo logs" ON photo_logs
    FOR DELETE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

-- Create storage bucket for skin photos
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'skin-photos',
    'skin-photos',
    false,  -- Private bucket
    10485760,  -- 10MB limit
    ARRAY['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
) ON CONFLICT (id) DO NOTHING;

-- RLS policy for storage bucket - users can only access their own photos
CREATE POLICY "Users can upload own photos" ON storage.objects
    FOR INSERT WITH CHECK (
        bucket_id = 'skin-photos' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Users can view own photos" ON storage.objects
    FOR SELECT USING (
        bucket_id = 'skin-photos' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Users can update own photos" ON storage.objects
    FOR UPDATE USING (
        bucket_id = 'skin-photos' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Users can delete own photos" ON storage.objects
    FOR DELETE USING (
        bucket_id = 'skin-photos' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers to update updated_at timestamp
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Sample data for testing (optional - remove in production)
-- INSERT INTO users (telegram_id, username, first_name, last_name)
-- VALUES (123456789, 'testuser', 'Test', 'User')
-- ON CONFLICT (telegram_id) DO NOTHING;

-- Comments for documentation
COMMENT ON TABLE users IS 'Stores Telegram user information and profile data';
COMMENT ON TABLE product_logs IS 'Tracks skincare products used by users with timestamps';
COMMENT ON TABLE trigger_logs IS 'Records skin irritation triggers experienced by users';
COMMENT ON TABLE symptom_logs IS 'Stores symptom severity ratings on a 1-5 scale';
COMMENT ON TABLE photo_logs IS 'Contains skin photos with AI analysis and metadata';

COMMENT ON COLUMN symptom_logs.severity IS 'Severity rating from 1 (very mild) to 5 (very severe)';
COMMENT ON COLUMN photo_logs.ai_analysis IS 'AI-generated analysis of the skin photo';
COMMENT ON COLUMN photo_logs.photo_url IS 'Supabase storage URL for the uploaded photo';