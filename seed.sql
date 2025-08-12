-- Seed default data for SkinTracker Database
-- Run this AFTER creating the schema to populate default products, triggers, and conditions

-- Insert global products (no user_id needed for global products)
INSERT INTO products (name, type, is_global) VALUES
  ('Cicaplast', 'Treatment', true),
  ('Azelaic Acid', 'Treatment', true),
  ('Enstilar', 'Treatment', true),
  ('Cerave Moisturizer', 'Moisturizer', true),
  ('Sunscreen', 'Protection', true),
  ('Retinol', 'Treatment', true),
  ('Niacinamide', 'Treatment', true),
  ('Salicylic Acid', 'Treatment', true),
  ('Hyaluronic Acid', 'Moisturizer', true),
  ('Vitamin C Serum', 'Treatment', true)
ON CONFLICT DO NOTHING;

-- Insert global triggers (no user_id needed for global triggers)
INSERT INTO triggers (name, emoji, is_global) VALUES
  ('Sun exposure', '☀️', true),
  ('Stress', '😰', true),
  ('Hot weather', '🌡️', true),
  ('Sweating', '💦', true),
  ('Spicy food', '🌶️', true),
  ('Alcohol', '🍷', true),
  ('Dairy products', '🥛', true),
  ('Lack of sleep', '😴', true),
  ('Hormonal changes', '🔄', true),
  ('New skincare product', '🧴', true)
ON CONFLICT DO NOTHING;

-- Insert default conditions (optional - remove if not needed)
INSERT INTO conditions (name, condition_type) VALUES
  ('Acne', 'existing'),
  ('Rosacea', 'existing'),
  ('Eczema', 'existing'),
  ('Psoriasis', 'existing'),
  ('Sensitive Skin', 'existing')
ON CONFLICT DO NOTHING;
