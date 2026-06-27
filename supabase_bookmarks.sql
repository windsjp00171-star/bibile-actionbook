-- 書籤：讀者標記的經節（無登入，以裝置 ID 當 user_id）
create table if not exists user_bookmarks (
  id bigserial primary key,
  user_id text not null,
  book_name text not null,
  chapter int not null,
  verse int not null,
  text text,
  created_at timestamptz default now(),
  unique (user_id, book_name, chapter, verse)
);
create index if not exists idx_bookmarks_user on user_bookmarks (user_id, created_at desc);
-- RLS：後端用 service_role 繞過；開 RLS 擋外部直連
alter table user_bookmarks enable row level security;
