---
name: 聖經全書 (bibile-actionbook)
description: 燭光下的手抄本：深棕書皮入口，羊皮紙米色閱讀頁，金色細線與三色經文標註。
colors:
  vellum: "#F7F0E0"
  vellum-card: "#FEF8EC"
  ink: "#2A1A08"
  ink-body: "#5A3A18"
  leather-night: "#1A0E06"
  leather: "#2C1A0E"
  leather-mid: "#3A220E"
  leather-edge: "#5C3010"
  gold: "#D4A847"
  gold-soft: "#C9A96E"
  gold-glow: "#F0C96A"
  gold-dim: "#9A7040"
  person-rust: "#8B3A1A"
  place-forest: "#2A5C3A"
  concept-indigo: "#4A3080"
  tour-flag: "#E94F37"
typography:
  body:
    fontFamily: "'Noto Serif TC', serif"
    fontSize: "15px"
    fontWeight: 300
    lineHeight: 2.3
    letterSpacing: "0.02em"
  title:
    fontFamily: "'Noto Serif TC', serif"
    fontSize: "20px"
    fontWeight: 500
    letterSpacing: "0.08em"
  cover:
    fontFamily: "'Noto Serif TC', serif"
    fontSize: "26px"
    fontWeight: 500
    lineHeight: 1.6
    letterSpacing: "0.2em"
  card-body:
    fontFamily: "'Noto Serif TC', serif"
    fontSize: "12px"
    fontWeight: 300
    lineHeight: 1.85
  label:
    fontFamily: "sans-serif"
    fontSize: "10px"
    fontWeight: 500
    letterSpacing: "0.12em"
rounded:
  sm: "3px"
  md: "6px"
  lg: "8px"
  card: "10px"
  pill: "99px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "32px"
components:
  nav-item:
    backgroundColor: "transparent"
    textColor: "#D4B080"
    typography: "{typography.card-body}"
    padding: "6px 16px"
  nav-item-active:
    backgroundColor: "{colors.leather-mid}"
    textColor: "{colors.gold-glow}"
  float-card:
    backgroundColor: "{colors.vellum-card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "14px 15px"
    width: "232px"
  testament-card:
    backgroundColor: "{colors.leather}"
    textColor: "{colors.gold}"
    rounded: "{rounded.card}"
    width: "140px"
    height: "155px"
  enter-button:
    backgroundColor: "#3D1F08"
    textColor: "{colors.gold}"
    rounded: "{rounded.md}"
    padding: "10px 28px"
  tour-fab:
    backgroundColor: "{colors.place-forest}"
    textColor: "#FFFFFF"
    rounded: "{rounded.pill}"
    padding: "12px 20px 12px 16px"
---

# Design System: 聖經全書

> 本檔記錄 **改版前的現況**，作為 Rule 18 導入順序的基準。其中標示「待重構」的是已知問題，不是要保留的規範。

## Overview

**Creative North Star: "燭光下的手抄本"**

整站是一本被翻開的老書：進站是深棕皮革的暗室，一本燙金書封等你點開；翻進去之後，是羊皮紙色的閱讀頁，經文行距寬鬆，像手抄本的行格。金色只用在細線、頁碼與點綴，從不用作大面積填色。氣氛安靜、有儀式感，偏靈修而不是工具。

同一套棕金色票出現在兩種亮度：入口與側欄是暗室（`leather` 系），閱讀與卡片是紙頁（`vellum` 系）。換頁就是換亮度，色相不變。

經文裡的標註是唯一允許出現的「彩色」：人名鏽紅、地名森綠、概念靛紫，其餘介面一律保持棕金。

**Key Characteristics:**
- 深棕皮革與羊皮紙兩種亮度，共用一組棕金色票
- 全站單一字體 Noto Serif TC，細字重 300 為主；標籤與徽章改用系統無襯線
- 金色細線與菱形（旋轉 45° 的 6px 方塊）作為分隔飾紋
- 經文行距 2.3，並有淡淡的橫格背景線（每 37px 一道）
- 入口有 3D 開書儀式動畫與星點背景（待重構）

## Colors

整體是低彩度的暖棕金，標註三色是唯一的彩度來源。

### Primary
- **鎏金 Gilt** (#D4A847)：入口的標題、邊框、星點、啟用態。暗底上才用；紙頁上改用較柔的 `gold-soft` (#C9A96E) 作細線與節號。
- **亮金 Gold Glow** (#F0C96A)：側欄目前章節文字，暗底上的選中強調。

### Secondary
- **森林綠 Forest** (#2A5C3A)：地名標註，也是教學浮動鈕與「確認類」按鈕的底色。這是介面裡唯一的實心強調色。

### Tertiary
- **鏽紅 Rust** (#8B3A1A)：人名標註。
- **靛紫 Indigo** (#4A3080)：概念標註。
- **教學紅點 Tour Flag** (#E94F37)：只出現在教學鈕脈動時的小圓點。

### Neutral
- **羊皮紙 Vellum** (#F7F0E0)：閱讀頁底色。
- **卡片紙 Vellum Card** (#FEF8EC)：浮動卡片、底部抽屜底色。
- **墨 Ink** (#2A1A08)：紙頁上的正文；內文次級用 `ink-body` (#5A3A18)。
- **夜皮革 Leather Night** (#1A0E06)：入口頁底色。
- **皮革 Leather** (#2C1A0E) / **皮革中 Leather Mid** (#3A220E) / **皮革緣 Leather Edge** (#5C3010)：側欄、選單卡、邊線，由深到淺。
- **暗金 Gold Dim** (#9A7040)：紙頁上的次要文字（章節標籤、說明）。

### Named Rules
**The Candle Rule.** 金色是光，不是顏料：只畫在線、點、字上，不鋪面。
**The Three Tags Rule.** 人名、地名、概念各一個色，介面其他元素不得借用這三個色來裝飾。

> 待清理：棕金色以十六進位硬編碼散落在 `static/style.css` 與 `templates/home.html` 內嵌樣式。兩處各自宣告一份 `:root`，`--bg`、`--gold` 同名但值不同（紙色 vs 夜皮革、`#C9A96E` vs `#D4A847`）；因為首頁不載入 `style.css`，目前不會在同一頁互相覆蓋，但新增共用元件時有踩雷風險，視覺改版時統一成單一來源。

## Typography

**Display / Body Font:** Noto Serif TC（fallback: serif），由 Google Fonts 載入，字重 300 / 400 / 500
**Label Font:** 系統 sans-serif（節號、徽章、小圖例、分類 pill）

**Character:** 中文宋體的細字重搭配寬鬆行距，像排版用心的線裝書；數字與英文小標用無襯線，形成「正文是書，標籤是書籤」的對比。

### Hierarchy
- **Cover** (500, 26px, 行高 1.6, 字距 0.2em)：入口書封的書名。
- **Title** (500, 20px, 字距 0.08em)：閱讀頁書卷名，置中。
- **Body** (300, 15px, 行高 2.3, 字距 0.02em)：經文。
- **Card body** (300, 12px, 行高 1.85)：浮動卡片內文。
- **Label** (500, 9–11px, 字距 0.12em, 大寫)：節號（上標）、徽章、圖例。

### Named Rules
**The Whisper Weight Rule.** 正文維持 300 細字重，只有標題與選中態升到 500。

> 待重構：節號 9px、卡片內文 12px、圖例 11px，在手機與長輩閱讀情境下偏小。

## Layout

桌面為「左側欄 + 單欄閱讀」：側欄固定 210px（可收合，狀態存 localStorage），閱讀區留白左右 48–52px，浮動卡片貼在右緣。手機（≤640px）側欄改為漢堡抽屜，卡片改為底部抽屜（最高 70vh）。首頁入口為全螢幕疊層，一次只顯示一個畫面，畫面之間以 .4s 淡入淡出切換。

間距沒有統一尺度，內嵌樣式與 `style.css` 都是逐處手寫的 px 值（多為 4 / 8 / 12 / 14 / 16 / 20）。

## Elevation & Depth

多數表面是平的，靠色階與金色細邊線分層。只有三處有陰影：入口書封（深色大陰影，製造立體感）、選單卡（`0 8px 32px rgba(0,0,0,.5)`）、浮動卡片（`2px 3px 0` 的淡金硬陰影，像紙片疊放）。

### Shadow Vocabulary
- **Book** (`box-shadow: 4px 4px 24px rgba(0,0,0,.7)`)：入口書封。
- **Menu** (`box-shadow: 0 8px 32px rgba(0,0,0,.5)`)：暗室選單卡。
- **Paper** (`box-shadow: 2px 3px 0 #C9A96E30`)：紙頁上的浮動卡片。
- **Tour FAB** (`box-shadow: 0 6px 22px rgba(42,92,58,.5)`)：教學浮動鈕。

### Named Rules
**The Flat Page Rule.** 紙頁上不使用柔和模糊陰影，疊層只用淡金硬陰影。

## Shapes

形體偏小圓角：按鈕與章節格 5–6px，卡片 8–10px，標籤與 pill 用全圓（99px）。書封是不對稱圓角（左 3px、右 10px），模擬書脊。分隔飾紋是兩端漸隱的金色 1px 線，中間一個旋轉 45° 的 6px 菱形。

## Components

### 側欄導覽
- **Style:** 皮革底，書名項 13px 淡金文字，書卷分組用 10px 大寫無襯線小標。
- **啟用態:** 底色 `leather-mid`，左緣 2px 金線，文字轉 `gold-glow`、字重 400。
- **篩選框:** 半透明黑底、`leather-mid` 邊、8px 圓角。

### 浮動卡片 / 底部抽屜
- **Corner Style:** 8px（桌面）／上緣 12px（手機抽屜）
- **Background:** `vellum-card`，1px `gold-soft` 邊
- **Shadow Strategy:** Paper 硬陰影；左側有 45° 旋轉的小箭頭指向被點的詞
- **內容:** 類型徽章（人／地／概念三色 pill）→ 名稱 15px → 說明 → 經文參照 chip

### 內文標註 (anno)
- **Style:** 文字轉為對應類型色，底部 2px 點狀線（色彩 53% 透明）。
- **State:** 點按後 `opacity .7`；整句可點的 `.clause` 在 hover 時浮現淡黃底。

### 入口按鈕與卡片
- **Testament card:** 140×155，皮革底、`leather-edge` 邊、10px 圓角，hover 改色並上移。
- **Book / chapter 格:** 6px / 5px 圓角，皮革底，hover 轉金。
- **Enter button:** 深棕底、金色邊與字、字距 0.1em。

### 教學浮動鈕 (Tour FAB)
- **Style:** 右下角固定，森林綠漸層膠囊，白字「？ 教學導覽」。
- **State:** 久未看過時脈動（1.8s 循環）並顯示右上紅點；`prefers-reduced-motion` 時關閉。

### 動畫 (入口與全站，待重構)
- **開書儀式:** 點書 → 書本繞 Y 軸轉 -28°（.8s `cubic-bezier(.4,0,.2,1)`）→ 600ms 後書本淡出 → 1100ms 後切到選單。**每次進站都必須點書才能進入**，且沒有跳過選項。
- **星點背景:** 40 顆隨機位置、2–5 秒不等的永久閃爍，由 JS 每次載入產生。
- **提示字與光暈:** `book-hint` 以 2s 循環呼吸；光暈 1s 淡入。
- **畫面切換:** 所有入口畫面共用 `.4s` 透明度過渡，切換期間舊畫面 `pointer-events: none`。
- **全站微互動:** hover / active 過渡約 .12–.25s；抽屜與卡片 .2–.25s 滑入。
- **降級:** 只有教學鈕脈動有 `prefers-reduced-motion` 降級；開書、星點、呼吸提示、畫面切換都沒有。

## Do's and Don'ts

### Do:
- **Do** 在暗底使用 `gold` (#D4A847)，在紙頁使用 `gold-soft` (#C9A96E)，兩者不互換。
- **Do** 保持正文 300 字重、行距 2.3，經文區留白。
- **Do** 用人名鏽紅、地名森綠、概念靛紫標註，並保持點狀底線樣式一致。
- **Do** 把分隔做成「漸隱金線 + 菱形」。

### Don't:
- **Don't** 在介面其他地方使用鏽紅、森林綠、靛紫來裝飾，三色專屬於標註（教學鈕與確認按鈕的森林綠為既有例外，待改版時釐清）。
- **Don't** 在紙頁上使用大面積實心金色或柔和模糊陰影。
- **Don't** 新增不在棕金色票內的灰色或藍色。

### 已知問題（待重構，非規範）
- 首頁入口：每次進站強制點書；星點永久動畫；除教學鈕外無 `prefers-reduced-motion` 降級。
- （已處理）`home.html` 內曾有無對應元素的閱讀區樣式，已於階段 2 移除。
- 色票以硬編碼十六進位散落兩處，兩份 `:root` 同名異值（目前不同頁、不衝突）。
- 小字（9–12px）偏多。
