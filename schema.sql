-- Skin Health Tracker Database Schema for Supabase
-- Execute this in Supabase SQL Editor to set up the database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table to store Telegram user information
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    reminder_time TEXT NOT NULL DEFAULT '09:00',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Products table to store reusable product definitions
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT,
    is_global BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Triggers table to store reusable trigger definitions
CREATE TABLE IF NOT EXISTS triggers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    emoji TEXT,
    is_global BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conditions table to store user skin conditions
CREATE TABLE IF NOT EXISTS conditions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    condition_type TEXT CHECK (condition_type IN ('existing', 'developed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Product logs table to track skincare products used
CREATE TABLE IF NOT EXISTS product_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_name TEXT NOT NULL,
    effect TEXT,
    notes TEXT,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trigger logs table to track skin irritation triggers
CREATE TABLE IF NOT EXISTS trigger_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trigger_name TEXT NOT NULL,
    notes TEXT,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Symptom logs table to track skin symptoms with severity ratings
CREATE TABLE IF NOT EXISTS symptom_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symptom_name TEXT NOT NULL,
    severity INTEGER NOT NULL CHECK (severity >= 1 AND severity <= 5),
    notes TEXT,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Photo logs table to store skin photos and AI analysis
CREATE TABLE IF NOT EXISTS photo_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    photo_url TEXT NOT NULL,
    ai_analysis TEXT,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Face embeddings table to enable face similarity search
CREATE TABLE IF NOT EXISTS face_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    photo_key TEXT NOT NULL,
    face_index INT NOT NULL,
    embedding VECTOR(512),
    det_score REAL,
    bbox JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS face_embeddings_vec_cos ON face_embeddings
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id);
CREATE INDEX IF NOT EXISTS idx_product_logs_user_id ON product_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_product_logs_logged_at ON product_logs(logged_at);
CREATE INDEX IF NOT EXISTS idx_triggers_user_id ON triggers(user_id);
CREATE INDEX IF NOT EXISTS idx_conditions_user_id ON conditions(user_id);
CREATE INDEX IF NOT EXISTS idx_trigger_logs_user_id ON trigger_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_trigger_logs_logged_at ON trigger_logs(logged_at);
CREATE INDEX IF NOT EXISTS idx_symptom_logs_user_id ON symptom_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_symptom_logs_logged_at ON symptom_logs(logged_at);
CREATE INDEX IF NOT EXISTS idx_photo_logs_user_id ON photo_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_photo_logs_logged_at ON photo_logs(logged_at);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_triggers_name ON triggers(name);
CREATE INDEX IF NOT EXISTS idx_conditions_name ON conditions(name);

-- Enable Row Level Security (RLS) for all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE triggers ENABLE ROW LEVEL SECURITY;
ALTER TABLE conditions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trigger_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE symptom_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE photo_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE face_embeddings ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
-- Users can only access their own data
CREATE POLICY "Users can view own data" ON users
    FOR SELECT USING (telegram_id = current_setting('request.telegram_id')::bigint);

CREATE POLICY "Users can update own data" ON users
    FOR UPDATE USING (telegram_id = current_setting('request.telegram_id')::bigint);

CREATE POLICY "Users can insert own data" ON users
    FOR INSERT WITH CHECK (telegram_id = current_setting('request.telegram_id')::bigint);

-- RLS Policies for products table
CREATE POLICY "Users can view own products" ON products
    FOR SELECT USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ) OR is_global = true);

CREATE POLICY "Users can insert own products" ON products
    FOR INSERT WITH CHECK (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can update own products" ON products
    FOR UPDATE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can delete own products" ON products
    FOR DELETE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

-- RLS Policies for triggers table
CREATE POLICY "Users can view own triggers" ON triggers
    FOR SELECT USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ) OR is_global = true);

CREATE POLICY "Users can insert own triggers" ON triggers
    FOR INSERT WITH CHECK (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can update own triggers" ON triggers
    FOR UPDATE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can delete own triggers" ON triggers
    FOR DELETE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

-- RLS Policies for conditions table
CREATE POLICY "Users can view own conditions" ON conditions
    FOR SELECT USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can insert own conditions" ON conditions
    FOR INSERT WITH CHECK (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can update own conditions" ON conditions
    FOR UPDATE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

CREATE POLICY "Users can delete own conditions" ON conditions
    FOR DELETE USING (user_id IN (
        SELECT id FROM users WHERE telegram_id = current_setting('request.telegram_id')::bigint
    ));

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

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_triggers_updated_at BEFORE UPDATE ON triggers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_product_logs_updated_at BEFORE UPDATE ON product_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trigger_logs_updated_at BEFORE UPDATE ON trigger_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_symptom_logs_updated_at BEFORE UPDATE ON symptom_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_photo_logs_updated_at BEFORE UPDATE ON photo_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Sample data for testing (optional - remove in production)
-- INSERT INTO users (telegram_id, username, first_name, last_name)
-- VALUES (123456789, 'testuser', 'Test', 'User')
-- ON CONFLICT (telegram_id) DO NOTHING;

-- Comments for documentation
COMMENT ON TABLE users IS 'Stores Telegram user information and profile data';
COMMENT ON TABLE products IS 'Reusable product definitions';
COMMENT ON TABLE triggers IS 'Reusable trigger definitions';
COMMENT ON TABLE product_logs IS 'Tracks skincare products used by users with timestamps and effects';
COMMENT ON TABLE trigger_logs IS 'Records skin irritation triggers experienced by users';
COMMENT ON TABLE symptom_logs IS 'Stores symptom severity ratings on a 1-5 scale';
COMMENT ON TABLE photo_logs IS 'Contains skin photos with AI analysis and metadata';
COMMENT ON TABLE face_embeddings IS 'Face embeddings and metadata for similarity search';

COMMENT ON COLUMN symptom_logs.severity IS 'Severity rating from 1 (very mild) to 5 (very severe)';
COMMENT ON COLUMN photo_logs.ai_analysis IS 'AI-generated analysis of the skin photo';
COMMENT ON COLUMN photo_logs.photo_url IS 'Supabase storage URL for the uploaded photo';

