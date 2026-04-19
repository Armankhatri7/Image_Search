-- Enable pgvector for embeddings
create extension if not exists vector;

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  username text not null unique,
  password_hash text not null,
  created_at timestamptz not null default now()
);

create table if not exists known_faces (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  person_name text not null,
  image_path text not null,
  face_embedding vector(128) not null,
  created_at timestamptz not null default now()
);

create table if not exists photos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  original_path text not null,
  annotated_path text,
  status text not null default 'processing',
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists detected_faces (
  id uuid primary key default gen_random_uuid(),
  photo_id uuid not null references photos(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  person_name text,
  bbox_top int not null,
  bbox_right int not null,
  bbox_bottom int not null,
  bbox_left int not null,
  face_embedding vector(128) not null,
  confidence float8 not null,
  created_at timestamptz not null default now()
);

create table if not exists summaries (
  id uuid primary key default gen_random_uuid(),
  photo_id uuid not null references photos(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  person_name text,
  summary_type text not null check (summary_type in ('overall', 'person')),
  summary_text text not null,
  embedding vector(3072) not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_known_faces_user_name on known_faces(user_id, person_name);
create index if not exists idx_photos_user_status on photos(user_id, status);
create index if not exists idx_summaries_user_name on summaries(user_id, person_name);
-- Note: ivfflat does not support vector dimensions above 2000.
-- Summaries currently use 3072-d embeddings, so we skip ANN index creation here.

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_photos_updated_at on photos;
create trigger trg_photos_updated_at
before update on photos
for each row execute procedure set_updated_at();
