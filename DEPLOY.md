# 部署到 Vercel

> 原本部署在 Railway，Railway 取消免費方案後專案被下架。現改用 Vercel
> serverless（免費、不休眠）。`Procfile` 保留著，任何吃 `gunicorn app:app`
> 的平台（Render / Fly / 自架）都還是能直接跑，`app.py` 本身沒有為了 Vercel
> 改動任何東西。

## 一、建快取表（Supabase）
在 Supabase 專案的 **SQL Editor** 貼上 `supabase_schema.sql` 全文，按 Run。
（沒做也能跑，只是快取重啟就失憶；做了才永久共用。）
書籤／閱讀進度／回饋另有 `supabase_bookmarks.sql`、`supabase_reading_progress.sql`、
`supabase_feedback.sql`。

## 二、Vercel 設定
1. Vercel → Add New Project → Import 這個 GitHub repo
2. Framework Preset 選 **Other**，Build/Output 全部留空——`vercel.json` 已經
   把所有路徑 rewrite 到 `api/index.py`，那支檔案只是 import 根目錄的 `app`，
   Vercel 的 Python runtime 會自動把它當 WSGI handler
3. 到 **Settings → Environment Variables** 加：

| 變數 | 值 | 必要 |
|---|---|---|
| `GROQ_API_KEY` | Groq key（這個 app 專用） | AI 解釋（擇一） |
| `GEMINI_API_KEY` | 或改用 Gemini key | AI 解釋（擇一） |
| `GEMINI_MODEL` | 用 Gemini 時建議填 `gemini-2.5-flash` | 選填 |
| `SUPABASE_URL` | Supabase 專案 URL | 快取／書籤／進度 |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | 同上 |
| `FLASK_SECRET_KEY` | 任意亂數字串 | 建議 |
| `EXPLAIN_DAILY_CAP` | 每日 AI 生成上限（預設 500） | 選填・成本保險絲 |

> 環境變數記得三個環境（Production / Preview / Development）都勾，不然
> preview 部署會少 key。改完要 **Redeploy** 才吃得到。

> AI 解釋的 provider 自動偵測：有 `GROQ_API_KEY` 優先用 Groq（快、免費），
> 否則用 `GEMINI_API_KEY`。兩個都沒設，閱讀與手刻標注照常，只是即時解釋停用。

## 三、驗證
- 開首頁 → 撒上17 應顯示標注（紅人名／綠地名／紫概念）
- 點地名 → 卡片含地圖
- **點一個分句** → 跳出 AI 解釋，切換兒童／慕道友／小組長深度不同
- 同一句點第二次 → 角落標「快取」、秒出（沒燒 API）

## 四、serverless 的兩個眉角
- **冷啟動**：`app.py` 在 import 時把 `cuv.json`(3.4M) + `entities.json`(0.8M)
  讀進記憶體，實測約 0.5 秒。之後同一個 instance 的請求都是熱的。
- **記憶體快取不跨 instance**：`vercel.json` 設了 `maxDuration: 30`、
  `memory: 1024`。AI 解釋的行程內快取在 serverless 下命中率低，真正的快取層
  是 Supabase——所以**務必把 Supabase 環境變數設好**，否則熱門經文會重複燒 API。

## 五、成本心法
三層快取：手刻字典 → Supabase 永久快取 → AI 只生成一次。
熱門經文幾天就被點滿快取，實際打到 API 的只有冷門首點，邊際成本趨近零。
