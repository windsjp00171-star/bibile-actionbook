# 部署到 Railway

## 一、建快取表（Supabase）
在 Supabase 專案的 **SQL Editor** 貼上 `supabase_schema.sql` 全文，按 Run。
（沒做也能跑，只是快取重啟就失憶；做了才永久共用。）

## 二、Railway 設定
1. Railway → New Project → Deploy from GitHub repo → 選這個 repo、分支 `claude/bible-reader-mvp-53pjjj`
2. Railway 會自動讀 `railway.json`（NIXPACKS 建置、gunicorn 啟動），不用額外設定
3. 到 **Variables** 加環境變數：

| 變數 | 值 | 必要 |
|---|---|---|
| `GROQ_API_KEY` | 你新開的 Groq key（這個 app 專用） | AI 解釋（擇一） |
| `GEMINI_API_KEY` | 或改用 Gemini key | AI 解釋（擇一） |
| `GEMINI_MODEL` | 用 Gemini 時建議填 `gemini-2.5-flash` | 選填 |
| `SUPABASE_URL` | Supabase 專案 URL | 快取永久化 |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | 快取永久化 |
| `EXPLAIN_DAILY_CAP` | 每日 AI 生成上限（預設 500） | 選填・成本保險絲 |

> AI 解釋的 provider 自動偵測：有 `GROQ_API_KEY` 優先用 Groq（快、免費），
> 否則用 `GEMINI_API_KEY`。兩個都沒設，閱讀與手刻標注照常，只是即時解釋停用。

## 三、驗證
- 開首頁 → 撒上17 應顯示標注（紅人名／綠地名／紫概念）
- 點地名 → 卡片含地圖
- **點一個分句** → 跳出 AI 解釋，切換兒童／慕道友／小組長深度不同
- 同一句點第二次 → 角落標「快取」、秒出（沒燒 API）

## 四、成本心法
三層快取：手刻字典 → Supabase 永久快取 → AI 只生成一次。
熱門經文幾天就被點滿快取，實際打到 API 的只有冷門首點，邊際成本趨近零。
