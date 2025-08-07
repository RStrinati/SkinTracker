-- Seed default symptoms, triggers, and conditions

-- Symptoms
INSERT INTO symptoms (name, is_custom) VALUES
  ('Redness', false),
  ('Burning', false),
  ('Itching', false),
  ('Dryness', false),
  ('Bumps', false)
ON CONFLICT (name) DO NOTHING;

-- Products
INSERT INTO products (name, is_global) VALUES
  ('Cicaplast', true),
  ('Azelaic Acid', true),
  ('Enstilar', true),
  ('Cerave Moisturizer', true),
  ('Sunscreen', true),
  ('Retinol', true),
  ('Niacinamide', true),
  ('Salicylic Acid', true)
ON CONFLICT (name) DO NOTHING;

-- Triggers
INSERT INTO triggers (name, is_global) VALUES
  ('Sun exposure', true),
  ('Stress', true),
  ('Hot weather', true),
  ('Sweating', true),
  ('Spicy food', true),
  ('Alcohol', true)
ON CONFLICT (name) DO NOTHING;

-- Conditions
INSERT INTO conditions (name, condition_type) VALUES
  ('Acne', 'existing'),
  ('Rosacea', 'existing'),
  ('Eczema', 'existing'),
  ('Psoriasis', 'existing'),
  ('Sensitive Skin', 'existing')
ON CONFLICT DO NOTHING;
