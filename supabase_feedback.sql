create table if not exists entity_feedback (
  id bigserial primary key,
  entity text not null,
  book text,
  chapter text,
  note text,
  created_at timestamptz default now()
);
