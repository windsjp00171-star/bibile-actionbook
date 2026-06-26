-- 首頁存檔：閱讀進度（無登入，以裝置 ID 當 user_id）
create table if not exists user_reading_progress (
  id bigserial primary key,
  user_id text not null,
  book_name text not null,
  chapter int not null,
  updated_at timestamptz default now(),
  unique (user_id, book_name)   -- 每位使用者每卷一筆，章節為最後讀到的
);

create index if not exists idx_progress_user_time
  on user_reading_progress (user_id, updated_at desc);
