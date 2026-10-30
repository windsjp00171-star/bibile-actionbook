# Surface brief: 讀經頁 (templates/read.html)

Mode: Read

## Decisions
- 範圍：全站一次改版（進入頁、選書流程、讀經頁、搜尋、列王年表）；世界從讀經頁定出，其他畫面沿用。
- 保留度：完全重新決定視覺世界，現況（燭光手抄本）只當證據。靈修的安靜感是產品原則，不是視覺限制。
- 進場儀式：保留儀式感，但可跳過、可降級；回訪者直接進入；動畫期間不得擋住點擊；`prefers-reduced-motion` 一律降級為瞬間切換。
- 長者友善：讀經頁以長輩為基準（經文字級、點擊目標、可預期操作）；首頁入口可較自由。

## Direction contract
THESIS: 讀經是跟著光走過一棟房子的剖面：一道晨光斜切過建築，你讀到哪，光就亮到哪。整個介面是一張連續的剖面圖，不是卡片堆。拒絕「米色紙頁加襯線體加棕金」這個宗教閱讀器預設。

OWN-WORLD: 灰泥白牆（#F2F1EC 偏冷的石灰白，非米黃）為經文底；剖面切開處的深炭灰實心塊（poche，#1F2328）作為導覽與結構；移動的日光金（#E2A62E）只當「現在讀到的位置」那一條光帶；退去的時刻用陰影藍（#5B6F8C）。人名、地名、概念用底線形式區分（實線／點線／雙線）並附淡色，不靠顏色單獨傳達。經文用 Noto Serif TC 400、1.0rem 起跳不低於 18px、行距 2.0；介面用 Noto Sans TC；時間與章節數字用等寬數字（tabular-nums）。建築剖面的細線（1px 炭灰）構成格線，註記釘在光的角度上。

STORY: 讀者相信這裡把經文讀得清楚，點一個詞就懂（人物、地圖、世系都在同一張剖面裡展開，不跳離經文）；知道自己讀到哪（光帶位置即進度）；下次回來光還停在上次的位置。

FIRST VIEWPORT: 左側 56px 炭灰窄欄為書卷剖面（66 卷是一排垂直窗格，目前這卷亮著日光金）；中間經文欄最大 40em，章節標題用大字、經節號用小而清楚的上標；右側為註記欄，點詞後註記沿著光的角度釘在該行旁（手機上變成底部抽屜）。頂端一條 2px 日光金細線隨捲動前進。主要動作是「讀下去」，次要是點詞與開地圖，位置皆在拇指可及範圍。

FORM: 晨光剖面（catalog id: architecture-inhabitable-space-daylight-section），排序第 4 位的挑戰者勝出；seed key 1989d4b5。

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
