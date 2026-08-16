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
2. Framework Preset 應該會自動偵測成 **Flask**，Build/Output 全部留空。
   Vercel 的 Flask 原生支援會在 `app.py`／`index.py`／`server.py`／`main.py`
   （根目錄或 `src/`、`app/`）裡找名為 `app` 的 Flask instance——本專案根目錄的
   `app.py` 正好符合，**不需要任何轉接檔或 rewrite**，整個 app 會變成一支
   Vercel Function，所有路徑都導進去。
   `vercel.json` 只做兩件事：`includeFiles` 確保 `cuv.json`／`data`／`templates`／
   `static` 進到 bundle，以及把 `maxDuration` 放寬到 30 秒給 AI 解釋用。
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

## 四、serverless 的三個眉角
- **冷啟動**：`app.py` 在 import 時把 `cuv.json`(3.4M) + `entities.json`(0.8M)
  讀進記憶體，實測約 0.5 秒。之後同一個 instance 的請求都是熱的。
- **記憶體快取不跨 instance**：AI 解釋的行程內快取在 serverless 下命中率低，
  真正的快取層是 Supabase——所以**務必把 Supabase 環境變數設好**，否則熱門經文
  會重複燒 API。
- **靜態檔走 function 不走 CDN**：Vercel 建議靜態檔放 `public/**` 由 CDN 送，
  但本專案的 `static/` 只有 72K，且模板都用 Flask 的 `url_for('static', ...)`，
  維持由 Flask 自己送（請求還是會進到同一支 function）。真的嫌慢再搬。

## 五、成本心法
三層快取：手刻字典 → Supabase 永久快取 → AI 只生成一次。
熱門經文幾天就被點滿快取，實際打到 API 的只有冷門首點，邊際成本趨近零。
