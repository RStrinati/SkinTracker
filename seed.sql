-- Seed default symptoms, triggers, and conditions

-- Symptoms
INSERT INTO symptoms (name, is_custom) VALUES
  ('Redness', false),
  ('Burning', false),
  ('Itching', false),
  ('Dryness', false),
  ('Bumps', false)
ON CONFLICT (name) DO NOTHING;

-- Triggers
INSERT INTO triggers (name, is_custom) VALUES
  ('Sun Exposure', false),
  ('Stress', false),
  ('New Product', false),
  ('Diet Change', false),
  ('Weather Change', false)
ON CONFLICT (name) DO NOTHING;

-- Conditions
INSERT INTO conditions (name) VALUES
  ('Acne'),
  ('Rosacea'),
  ('Eczema'),
  ('Psoriasis'),
  ('Sensitive Skin')
ON CONFLICT (name) DO NOTHING;
