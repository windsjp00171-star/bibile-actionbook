---
name: 聖經全書 (bibile-actionbook)
description: 晨光剖面：灰泥白牆上的經文、炭灰剖面塊的導覽，一道移動的日光金標示讀到哪裡。
colors:
  wall: "#F2F1EC"
  wall-2: "#E9E8E1"
  wall-3: "#DAD9D0"
  paper: "#FAFAF7"
  ink: "#1C1F23"
  ink-2: "#3B4047"
  ink-3: "#4A5058"
  ink-4: "#666C75"
  poche: "#1F2328"
  poche-2: "#2B3036"
  poche-3: "#3A4048"
  poche-ink: "#C3C8CF"
  poche-mute: "#8C95A1"
  entry-ground: "#14171A"
  sun: "#E2A62E"
  sun-glow: "#F2C45A"
  sun-deep: "#8A5A0B"
  shade: "#5B6F8C"
  action: "#2B3A4E"
  action-deep: "#1F2A3A"
  person: "#9A3B26"
  place: "#2F6B4A"
  concept: "#55438F"
typography:
  scripture:
    fontFamily: "'Noto Serif TC', serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 2
    letterSpacing: "0.02em"
  ui:
    fontFamily: "'Noto Sans TC', system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
  title:
    fontFamily: "'Noto Serif TC', serif"
    fontSize: "26px"
    fontWeight: 500
    letterSpacing: "0.12em"
  entry:
    fontFamily: "'Noto Serif TC', serif"
    fontSize: "36px"
    fontWeight: 600
    letterSpacing: "0.32em"
  verse-num:
    fontFamily: "'Noto Sans TC', system-ui, sans-serif"
    fontSize: "0.72em"
    fontWeight: 500
rounded:
  sm: "6px"
  md: "8px"
  lg: "10px"
  pill: "99px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "32px"
components:
  nav-item:
    backgroundColor: "transparent"
    textColor: "{colors.poche-ink}"
    padding: "8px 16px"
  nav-item-active:
    backgroundColor: "{colors.poche-2}"
    textColor: "{colors.sun-glow}"
  chapter-pill:
    backgroundColor: "{colors.poche-2}"
    textColor: "{colors.poche-ink}"
    rounded: "{rounded.sm}"
    size: "40px"
  tool-button:
    backgroundColor: "{colors.action}"
    textColor: "#FFFFFF"
    rounded: "{rounded.pill}"
  entry-button:
    backgroundColor: "transparent"
    textColor: "{colors.sun-glow}"
    rounded: "{rounded.md}"
    height: "56px"
  float-card:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "14px 15px"
  tour-fab:
    backgroundColor: "{colors.poche}"
    textColor: "#FFFFFF"
    rounded: "{rounded.pill}"
---

# Design System: 聖經全書

## Overview

**Creative North Star: "晨光剖面"**

整個介面是一張連續的建築剖面：灰泥白牆是經文所在的房間，炭灰實心塊是切開的牆體與導覽，一道日光金斜切過畫面，讀到哪裡，光就亮到哪裡。它回應的是靈修的時間感（晨更），而不是宗教閱讀器常見的米色紙頁加棕金。

氣氛安靜、清楚、不裝飾。顏色幾乎都是灰階，只有日光金代表「現在的位置」，只有人名、地名、概念三個標註色承載語意。標註同時用底線形式區分，不單靠顏色。

**Key Characteristics:**
- 冷調石灰白牆（#F2F1EC）加炭灰剖面塊，不使用米黃或棕色
- 日光金只出現在三處：頂端進度光帶、導覽中目前所在、入口的一道斜光
- 經文用襯線 Noto Serif TC 400、18px 起、行距 2；介面用 Noto Sans TC
- 人物＝實線、地點＝點線、概念＝雙線，色弱也能分辨
- 入口動畫只有一道 240ms 的斜光，回訪者直接進入

## Colors

### Primary
- **日光金 Sun** (#E2A62E)：進度光帶、入口斜光、焦點外框。**亮日光 Sun Glow** (#F2C45A)：暗底上的選中文字。**深日光 Sun Deep** (#8A5A0B)：淺底上需要金色文字時才用。

### Secondary
- **陰影藍 Shade** (#5B6F8C)：退去的時刻、次要資訊。**行動藍灰 Action** (#2B3A4E)：工具按鈕、連結、主要動作底色。

### Tertiary（標註專用）
- **鏽紅 Person** (#9A3B26)、**森綠 Place** (#2F6B4A)、**靛紫 Concept** (#55438F)。

### Neutral
- **牆 Wall** (#F2F1EC)、**牆 2** (#E9E8E1)、**牆 3** (#DAD9D0)：閱讀底、面板、分隔線。**卡片紙 Paper** (#FAFAF7)：浮動卡片。
- **墨 Ink** (#1C1F23) 到 **ink-4** (#666C75)：正文到次要文字，ink-4 在牆上對比約 4.9:1。
- **剖面 Poche** (#1F2328)、**poche-2** (#2B3036)、**poche-3** (#3A4048)：側欄、入口選單。**入口底 Entry Ground** (#14171A)。

### Named Rules
**The One Beam Rule.** 日光金只代表「現在的位置」。不用它做裝飾、不鋪面。
**The Three Tags Rule.** 鏽紅、森綠、靛紫專屬標註。**The Form Not Hue Rule.** 標註類型必須同時用底線形式區分。

## Typography

**Scripture:** Noto Serif TC，**UI:** Noto Sans TC，數字用 `tabular-nums`。

### Hierarchy
- **Entry** (600, 36px, 字距 0.32em)：入口書名。
- **Title** (500, 26px, 字距 0.12em)：書卷名。
- **Scripture** (400, 18px 可由使用者調整, 行距 2)：經文，行寬約 640px。
- **UI** (400–500, 12–15px)：導覽、按鈕、卡片。字級下限 12px。
- **Verse number** (500, 0.72em, tabular-nums)：節號。

## Layout

桌面：左側 210px 炭灰剖面欄（可收合）加單欄經文，經文最大寬約 640px。手機（≤640px）：側欄收成抽屜，說明卡變底部抽屜。頂端 3px 日光進度光帶固定。章節按鈕最小 40px。

## Elevation & Depth

平面為主，靠色階與剖面塊分層。浮動卡片用柔和的小陰影；入口選單卡 `0 4px 14px rgba(0,0,0,.35)`。

## Shapes

圓角只有四階：4px（行內標註）、8px（按鈕、格、卡片）、12px（面板、底部抽屜）、全圓（工具列按鈕、標籤、路線晶片）。分隔飾紋是日光金菱形與細線。

## Components

### 側欄導覽
炭灰底，書名項 poche-ink，啟用態 poche-2 底加亮日光文字。章節按鈕 40px，已讀有小金點。

### 浮動卡片 / 底部抽屜
Paper 底、1px 淺灰邊、8px 圓角；內容順序：類型徽章 → 名稱 → 說明 → 經文參照。

### 內文標註
人物實線 2px、地點點線 2px、概念雙線 3px，皆為對應類型色。

### 入口
炭灰底，書名 36px，一個 56px 高的「進入」按鈕，一道日光金斜線。首次或 30 天未訪才顯示；回訪者直接進入選單。

### 教學導覽
聚焦圈用日光金外框，彈窗 Paper 底，主要按鈕行動藍灰；右下角浮動鈕炭灰底。

### 動畫
入口斜光 240ms；面板與抽屜滑動約 200–250ms。`prefers-reduced-motion: reduce` 時全部降為近乎瞬間。動畫期間所有控制項可點擊。

## Do's and Don'ts

### Do:
- **Do** 讓日光金只代表現在的位置。
- **Do** 標註類型同時用顏色與底線形式區分。
- **Do** 保持字級下限 12px、經文 18px 起、點擊目標 40px 起。

### Don't:
- **Don't** 重新引入米黃、棕色或棕金。
- **Don't** 用三個標註色裝飾其他元素。
- **Don't** 在動畫期間用遮罩或 `pointer-events: none` 擋住操作。

### 已知待處理
- 無。字級已收斂為 12 / 13 / 14 / 16 / 18 / 22 / 26px，圓角為 4 / 8 / 12px 與全圓。
