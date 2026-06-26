-- 聖經互動閱讀器 — Supabase 結構
-- 在 Supabase SQL Editor 執行一次即可。沒有這張表 app 仍可運作（降級為記憶體快取）。

-- AI 解釋的永久快取：每個「選取文字＋程度」只生成一次，之後全域共用、零成本。
-- 這張表會隨使用自動長成一份標注資料庫；日後可人工審核把好的內容升級為已校訂。
create table if not exists ai_explanations (
    cache_key      text primary key,           -- sha1(level|text)
    selected_text  text not null,              -- 使用者選取的經文
    level          text not null,              -- child / seeker / leader
    content        text not null,              -- 解釋內容
    ref            text,                        -- 出處，例如「路得記 第1章」
    verified       boolean default false,       -- 人工是否已校訂（true 表示可信度更高）
    created_at     timestamptz default now()
);

create index if not exists idx_ai_expl_text on ai_explanations (selected_text);

-- 服務端使用 service role key 存取（繞過 RLS），故此處不另設 RLS 政策。
