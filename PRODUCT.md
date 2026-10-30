# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
教會會眾與靈修讀者，閱讀中文和合本聖經。使用者含長輩與不熟科技的同工，多在手機或電腦上逐卷讀經，遇到生僻的人名、地名、制度才點開說明。

受眾事實（讀經頁以此為基準）：
- 會在畫面還沒反應時連點。
- 怕按錯而不敢操作。
- 小字閱讀困難。
- 動畫不得擋住操作：播放期間目標元素必須已可點擊，且需提供 `prefers-reduced-motion: reduce` 降級。

長者友善依使用場景套用：讀經頁（含卡片、地圖、搜尋、教學）以此為準；首頁入口可較自由，但不得讓人進不了站。

## Product Purpose
互動聖經閱讀網站，讓聖經文字從平面、有隔閡感的古文變回立體、真實：地點是真實地理、異象有具體畫面、律法有實際內容，而不是模糊的古代名詞堆砌。成功是讀者能順暢讀下去，卡住時點一下就懂，不用離開經文。

## Positioning
核心是 context-aware 標註引擎：經文裡的人名、地名、族名可點，跳出背景卡片、地圖與世系圖，並能依書卷與章節區分同名人物。資料由人工逐卷核對，準確優先於數量，並經牧者覆核同名人物分流。

## Operating Context
- 經文為《和合本》（1919），公有領域，存於本機 `cuv.json`，不依賴外部 API。
- 標註資料唯一來源是 `data/entities.json`（詞條）與 `data/relationships.json`（人物關係）；另有 `routes.json`（旅程路線）與 `kings_timeline.json`。
- 標註是字面比對：詞條鍵必須是經文逐字出現的字串。
- 擁有者逐卷讀經、有疑問才回報，資料持續增補中。
- 現有技術：Flask + Jinja、Leaflet 地圖、vanilla JS、PWA（`sw.js`、`manifest.json`），部署於 Vercel。

## Capabilities and Constraints
- 功能：逐章閱讀、點按標註卡片、地圖與旅程路線動畫、家族世系圖、經文搜尋、列王年表、書籤與閱讀進度、經文回報、聚焦式教學導覽。
- 神學紅線：只寫各宗派共同承認的經文事實層面，不涉及救恩論、教會論、洗禮方式、預定論等分歧議題；有不同看法時以「有不同看法」帶過。
- 準確優先於數量：位置不詳或關係不確定的族譜寧可跳過。
- 技術約束：不得刪改 `data-tour`、表單 name、JS 依賴的 id、Jinja 結構；改版前後 `data-tour` 數量一致。
- 未決定：Supabase 目前未實際使用，是否保留待定。

## Brand Commitments
站名「聖經全書」。氣質為安靜、有靈修感；神學正統性不可退讓。視覺方向由 Impeccable 流程重新決定，現況記錄於 `DESIGN.md`。

## Evidence on Hand
- 《和合本》全文：`cuv.json`。
- 詞條與關係資料：`data/entities.json`（兩千七百餘個鍵）、`data/relationships.json`。
- 牧者覆核表：`PASTOR_REVIEW.md`；標註稽核報告：`AUDIT_REPORT.md`。
- 沒有使用者統計、評價或見證資料，不得捏造。

## Product Principles
1. 準確永遠優先於數量；不確定就不標、不連。
2. 具體而非百科：讓讀者看得到畫面，止於此，其餘留給讀經本身。
3. 介面退後，經文為主：標註與卡片服務閱讀，不打斷閱讀。
4. 寧缺勿錯的資料原則高於畫面好看。
5. 動畫與入口儀式不得成為進入或操作的必要路徑。

## Accessibility & Inclusion
讀經頁以長輩與不熟科技者為基準：經文與說明文字夠大、點擊目標足夠、操作可預期、出錯可復原。所有動畫提供 `prefers-reduced-motion` 降級，且不得遮擋互動。繁體中文，語氣適合非技術使用者。
