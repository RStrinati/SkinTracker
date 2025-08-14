-- === Extensions (idempotent) ================================================
-- gen_random_uuid() comes from pgcrypto; safe to enable if not already
create extension if not exists "pgcrypto";
-- (Optional) If you prefer uuid_generate_v4(), also enable uuid-ossp:
-- create extension if not exists "uuid-ossp";

-- === Table (idempotent) =====================================================
create table if not exists skin_kpis (
    id uuid primary key default gen_random_uuid(), -- or uuid_generate_v4()
    user_id uuid not null references users(id) on delete cascade,
    image_id text not null,                             -- links to photo filename/hash
    "timestamp" timestamptz not null,                   -- analysis time

    -- Face analysis metrics
    face_area_px integer not null,                      -- face area in pixels

    -- Blemish analysis metrics
    blemish_area_px integer not null,                   -- total blemish area in pixels
    percent_blemished real not null,                    -- % of face area with blemishes

    -- Analysis image paths (Supabase storage keys/paths)
    face_image_path text not null,
    blemish_image_path text not null,
    overlay_image_path text not null,

    -- Metadata
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- === Indexes (idempotent) ===================================================
create index if not exists idx_skin_kpis_user_id            on skin_kpis(user_id);
create index if not exists idx_skin_kpis_image_id           on skin_kpis(image_id);
create index if not exists idx_skin_kpis_timestamp          on skin_kpis("timestamp");
create index if not exists idx_skin_kpis_percent_blemished  on skin_kpis(percent_blemished);

-- (Optional) enforce 1 record per image per user per exact timestamp
-- create unique index if not exists uq_skin_kpis_user_img_ts
--   on skin_kpis(user_id, image_id, "timestamp");

-- === Trigger function (idempotent) ==========================================
-- Creates/refreshes a generic "updated_at" function if you don't already have one
create or replace function update_updated_at_column()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- === Trigger (refresh safely) ===============================================
drop trigger if exists update_skin_kpis_updated_at on skin_kpis;
create trigger update_skin_kpis_updated_at
before update on skin_kpis
for each row execute function update_updated_at_column();

-- === Row Level Security =====================================================
alter table skin_kpis enable row level security;

-- Recreate policies idempotently (drop-then-create avoids 42710 name clashes)
drop policy if exists "Users can view own skin kpis"   on skin_kpis;
drop policy if exists "Users can insert own skin kpis" on skin_kpis;
drop policy if exists "Users can update own skin kpis" on skin_kpis;
drop policy if exists "Users can delete own skin kpis" on skin_kpis;

-- SELECT: a user can see only their own rows
create policy "Users can view own skin kpis"
on skin_kpis
for select
using (user_id = auth.uid());

-- INSERT: user can insert rows only for themselves
create policy "Users can insert own skin kpis"
on skin_kpis
for insert
with check (user_id = auth.uid());

-- UPDATE: user can update only their own rows
create policy "Users can update own skin kpis"
on skin_kpis
for update
using (user_id = auth.uid())
with check (user_id = auth.uid());

-- DELETE: user can delete only their own rows
create policy "Users can delete own skin kpis"
on skin_kpis
for delete
using (user_id = auth.uid());

-- === Comments (idempotent by nature) ========================================
comment on table  skin_kpis is 'Stores quantitative skin analysis metrics and KPIs from photo processing';
comment on column skin_kpis.face_area_px        is 'Total detected face area in pixels';
comment on column skin_kpis.blemish_area_px     is 'Total area of detected blemishes in pixels';
comment on column skin_kpis.percent_blemished   is 'Percentage of face area affected by blemishes (0-100)';
comment on column skin_kpis.face_image_path     is 'Storage path to face detection visualization';
comment on column skin_kpis.blemish_image_path  is 'Storage path to blemish analysis visualization';
comment on column skin_kpis.overlay_image_path  is 'Storage path to combined analysis overlay';
