# 部署到 Vercel

> 原本部署在 Railway，Railway 取消免費方案後專案被下架。現改用 Vercel
> serverless（免費、不休眠）。`Procfile` 保留著，任何吃 `gunicorn app:app`
> 的平台（Render / Fly / 自架）都還是能直接跑，`app.py` 本身沒有為了 Vercel
> 改動任何東西。

## 一、建資料表（Supabase）
在 Supabase 專案的 **SQL Editor** 依序貼上並執行：
`supabase_bookmarks.sql`（書籤）、`supabase_reading_progress.sql`（閱讀進度）、
`supabase_feedback.sql`（標註回報）。沒建也能讀經，只是這三項功能不會留存。

## 二、Vercel 設定
1. Vercel → Add New Project → Import 這個 GitHub repo
2. Framework Preset 應該會自動偵測成 **Flask**，Build/Output 全部留空。
   Vercel 的 Flask 原生支援會在 `app.py`／`index.py`／`server.py`／`main.py`
   （根目錄或 `src/`、`app/`）裡找名為 `app` 的 Flask instance——本專案根目錄的
   `app.py` 正好符合，**不需要任何轉接檔或 rewrite**，整個 app 會變成一支
   Vercel Function，所有路徑都導進去。
   `vercel.json` 只做兩件事：`includeFiles` 確保 `cuv.json`／`data`／`templates`／
   `static` 進到 bundle，以及 `maxDuration`。
3. 到 **Settings → Environment Variables** 加：

| 變數 | 值 | 必要 |
|---|---|---|
| `SUPABASE_URL` | Supabase 專案 URL | 書籤／進度／回報 |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | 同上 |
| `FLASK_SECRET_KEY` | 任意亂數字串 | 建議 |

> 環境變數記得三個環境（Production / Preview / Development）都勾，不然
> preview 部署會少 key。改完要 **Redeploy** 才吃得到。

## 三、驗證
- 開首頁 → 撒上17 應顯示標註（紅人名／綠地名／紫概念）
- 點地名 → 卡片含地圖
- 點人名 → 卡片含關係與世系
- 桌面版左上箭頭可收合書卷側欄，重新整理後狀態保留

## 四、serverless 的兩個眉角
- **冷啟動**：`app.py` 在 import 時把 `cuv.json`(3.4M) + `entities.json`(0.8M)
  讀進記憶體，實測約 0.5 秒。之後同一個 instance 的請求都是熱的。
- **靜態檔走 function 不走 CDN**：Vercel 建議靜態檔放 `public/**` 由 CDN 送，
  但本專案的 `static/` 只有 72K，且模板都用 Flask 的 `url_for('static', ...)`，
  維持由 Flask 自己送（請求還是會進到同一支 function）。真的嫌慢再搬。

## 五、bundle 500MB 硬限制（踩過兩次，別再踩）

Vercel 的 function bundle 上限是 **500MB**，超過直接建置失敗：

```
Error: Total bundle size (616.03 MB) exceeds the maximum function size (500 MB).
```

真的炸過。**有兩個成因，缺一個都修不好**：

### 成因一：`includeFiles` 不能寫 `"**"`

`uv` 會在建置時把 venv 建在專案目錄裡，`"**"` 會連它一起掃進 bundle，
等於相依被算兩次。更糟的是 Vercel 預設會 **Restored build cache from prev**，
快取裡那個裝著舊套件的 venv 還在，所以光從 `requirements.txt` 拿掉套件
**bundle 也不會變小**（這就是第二次失敗的原因）。

所以 `includeFiles` 一定要寫成明確清單，讓它不可能掃到建置產物：

```json
"includeFiles": "{cuv.json,data/**,templates/**,static/**}"
```

目前這個 pattern 納入 20 個檔案、4.34MB。改動時務必重新確認 `cuv.json`
有被納入——漏掉的話網站會部署成功但每一章都「查無此章經文」。

> 如果改完仍然失敗，到 Vercel 按 Redeploy 時把 **Use existing Build Cache
> 取消勾選**，強制丟掉舊快取。

### 成因二：相依套件的體重

歷史紀錄：`google-generativeai` 曾經把 site-packages 從 68MB 撐到 219MB
（它會拖進 `google-api-python-client` 103MB + `google` 25MB + `grpc` 19MB）。
AI 解釋功能後來整個移除，這顆相依也跟著消失了。

新增相依前先量一下：

```bash
python3 -m venv /tmp/sz && /tmp/sz/bin/pip install -r requirements.txt
du -sh /tmp/sz/lib/python3.*/site-packages
```

本機 site-packages 抓在 200MB 以內大致安全。`requirements.txt` 只放網站真正
需要的東西；`tools/`、`scripts/` 的離線工具相依放 `requirements-dev.txt`，
不會進到 bundle。
