# 聖經互動全書 — 實作說明書與報告

一套「讓讀者讀經時，看不懂的專名、難詞、世系都能就地點開看懂」的互動聖經閱讀器。
核心理念：**不是整本白話註釋，而是把艱澀專名、人名、地名、世系「正確地」標出來。準確優先於數量。**

---

## 一、技術架構

| 項目 | 內容 |
|---|---|
| 後端 | 單檔 Flask（`app.py`） |
| 經文資料 | `cuv.json`（和合本全本，啟動載入記憶體） |
| 標註資料 | `data/entities.json`（詞條字典） |
| 關係資料 | `data/relationships.json`（人物關係圖） |
| 前端 | Jinja2 模板 + 原生 JS；地圖用 Leaflet.js |
| 資料庫 | Supabase（存檔、AI快取、回報） |
| 部署 | Railway（追 main 自動部署） |

---

## 二、核心功能

### 1. 脈絡感知標註引擎（護城河）
經文中的專名自動加底線、點擊看背景卡。和市面字典式標註的差別：**會看上下文判斷哪個才對**。

四層消歧義（`_resolve_entity`）：
1. **書卷+章節**：精確到某書某章（如以諾在創4=該隱之子、創5=與神同行）
2. **書卷**：限定在某些書卷出現
3. **約別**：舊約/新約（如猶大支派 vs 加略人猶大）
4. **通用**：任何地方

再加兩層動態判斷：
- **同節關鍵字轉址**（`context_redirect`）：本節出現特定字就改指向（如「約翰…施洗」→施洗約翰）
- **緊前頭銜轉址**（`prefix_redirect`）：名字前的頭銜（如「以色列王」約蘭 vs「猶大王」約蘭）

防誤框機制：
- **最長匹配**：詞條按長度排序，長名優先（「以色列人」整框，不切成「以色列」+「人」）
- **碎片守衛**（`_EXT_GUARD`）：短名落在更長名字裡時不框（如「利亞」不框進「米利亞」）
- **單字白名單**（`_SINGLE_CHAR_OK`）：單字詞預設不標，僅放行安全的（如「肘」總接在數字後）

### 2. 本章世系結構圖（差異化）
列王紀、歷代志、家譜章節最難讀——腦中拼不出結構。有家譜/王系的章節出現「⛓ 本章世系結構圖」按鈕，開啟 SVG 樹狀圖：
- **本章人物亮色點亮、脈絡人物淡顯**，點任一人看介紹
- 演算法（`chapter_lineage`）：以本章「解析為人物」者為核心，連接彼此 + 一層脈絡，**不無謂追溯到亞當**
- 防交錯排序：子女依父母平均位置排列
- 用解析後身分判斷 `owns_relationships`：避免把使徒雅各誤接成族長家譜

### 3. 互動地圖
地名卡片內嵌 Leaflet 小地圖（焦點地名固定標籤、其他地名點擊顯名避免擁擠），可「⛶ 放大地圖」到全螢幕大圖，所有地名標清楚、自動框住全部地點、點地名跳轉。

### 4. 分齡 AI 解釋
卡片內「✦ AI 深入解釋」按鈕，依程度（兒童/慕道友/小組長）生成解釋。三層快取控成本：手刻字典 → Supabase 永久快取 → Groq/Gemini 即時生成（受每日上限保護）。

### 5. 人物關係網（聖經宇宙）
卡片底部顯示關係 chip（父母/子女/手足/配偶/敵對/師長/門生/同工），點 chip 跳到那個人，可一層層在人物宇宙裡遊走。

### 6. 首頁流程
開書動畫（星點背景、點書本→光芒→淡出）→ 存檔選單（最近兩筆閱讀紀錄）→ 三層選書（新舊約→經卷→章節）→ 導向閱讀頁。

### 7. 回報機制
- **標錯**：卡片上按「⚑ 標註有誤」
- **漏標**：閱讀頁底「⚑ 本章有漏標或標錯？回報」，打字描述
- 都進 Supabase `entity_feedback` 表

---

## 三、詞條資料結構（`entities.json`）

值可為**單一物件**或**消歧義陣列**：

```jsonc
// 單一
"摩西": {"type":"person","name":"摩西","name_en":"Moses","testament":"both","desc":"...","verses":"..."}

// 消歧義（同名不同人）
"約蘭": [
  {"name":"約蘭","prefix_redirect":[{"prefix":["以色列王","哈的兒子"],"target":"約蘭（以色列王）"},...]},
  ...
]
```

欄位：`type`(person/place/concept)、`name`、`name_en`、`desc`、`verses`、`testament`(OT/NT/both)、
`books`、`chapters`[lo,hi]、`lat`/`lng`（地點）、`context_redirect`、`prefix_redirect`、`rel_owner`。

**詞條規模**：約 586 條，涵蓋人物、地名、概念，及系統性補完的類別——
祭司器物（胸牌/烏陵/土明/以弗得）、香料藥材（沒藥/乳香/哪噠）、度量衡（肘/伊法/他連得）、
礦石（十二寶石）、官職（百夫長/酒政）、疾病（大痲瘋/血漏）、植物樹木、樂器、節期、
民族列國（迦南七族/五旬節萬國名單）等。

**彌賽亞主幹世系**已串連：亞當→挪亞→閃→亞伯拉罕→猶大→法勒斯→…→大衛→列王，
使創世記族譜、路得記4、馬太1 連成一棵連續的樹。

---

## 四、API 接口

| 端點 | 方法 | 用途 |
|---|---|---|
| `/` | GET | 首頁（開書動畫→選書） |
| `/read/<book>/<chapter>` | GET | 閱讀頁（標註、地圖、世系圖） |
| `/api/books` | GET | 選書資料 `{ot:[{order,name,chapters}],nt:[...]}` |
| `/api/progress` | GET/POST | 存檔讀寫（裝置ID當user_id） |
| `/api/explain` | POST | AI 解釋（三層快取） |
| `/api/feedback` | POST | 標註回報 |

---

## 五、Supabase 資料表

| 表 | 欄位 | 用途 |
|---|---|---|
| `user_reading_progress` | user_id, book_name, chapter, updated_at | 首頁存檔（`supabase_reading_progress.sql`） |
| `entity_feedback` | entity, book, chapter, note, created_at | 標註回報（`supabase_feedback.sql`） |
| `ai_explanations` | cache_key, content | AI 解釋永久快取（`supabase_schema.sql`） |

無登入系統，存檔以前端產生的「裝置 ID」（localStorage `bible-device-id`）識別。

---

## 六、維護工作流（定期修訂）

**設計目標：不靠 Claude 掃全本（省 token），靠回報驅動精修。**

1. 讀者平常閱讀，看到標錯/漏標就按「⚑ 回報」→ 進 `entity_feedback` 表
2. 定期處理時：用 Supabase 工具讀 `entity_feedback` 表，一次看完所有回報
3. 批次修：依回報的書卷章節，確認經文背景後改 `entities.json`（或加消歧義規則）
4. commit → PR → merge → Railway 自動部署

**修訂原則**：
- 先確認經文背景再下註解（同名不同人務必依上下文）
- 族譜「誰生誰、誰繼承誰」除非神學關鍵，否則略過
- 位置不可考的地點就不勉強標座標
- 準確永遠優先於數量

---

## 七、部署備忘

```bash
pip install -r requirements.txt
gunicorn app:app          # 生產
flask run                 # 開發
```

環境變數：`SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY`、`GROQ_API_KEY`、`GEMINI_API_KEY`、`FLASK_SECRET_KEY`。

上線前確認三張 Supabase 表已建立（跑對應的 `.sql`）。

---

## 八、輔助工具

- `scripts/auto_fill_entities.py`：用 Groq 從經文掃高頻詞、批次生成詞條（跑在自己機器/Railway，用自己的 Groq key，不燒 Claude token）
- `AUDIT_REPORT.md`：標註資料稽核報告
- `PASTOR_REVIEW.md`：同名人物判讀表（供牧者覆核）
