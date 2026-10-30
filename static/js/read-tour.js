// ── 聚焦式教學導覽（SpotlightTour，static/js/tour.js） ─────────────
// 深入式導覽：每一步「先打開該模塊面板」，再圈裡面的控制項
function closeAllPanels() {
  ['closeCard', 'closeSearch', 'closeExplore', 'closeBookMap', 'closeRoutes', 'closeBookmarks'].forEach(fn => {
    try { if (typeof window[fn] === 'function') window[fn](); } catch (e) {}
  });
}
const PAGE_TOUR_STEPS = [
  { title: '歡迎！這是教學導覽 👋', text: '不會用沒關係～我會把這一頁的功能一個一個打開、圈出來、用白話說給你聽。看著綠色框框、按「下一步」就好；想停隨時按「結束導覽」。' },
  { sel: '[data-tour="legend"]', title: '標註說明', text: '經文中有底線的詞，分人物（紅）、地點（綠）、族群／概念（紫）三類。', spot: 6 },
  { sel: '[data-tour="anno"]', title: '點詞看背景', text: '點任一個有底線的詞，會跳出小卡片：人物生平、地點地圖、概念解釋（生僻字還附注音）。我現在幫你打開一張看看。', spot: 4 },
  { before: () => { const a = document.querySelector('[data-tour="anno"]'); if (a) a.click(); }, beforeWait: 380,
    sel: '[data-tour="card-verses"]', title: '卡片：列出所有經節', text: '卡片下方這顆「🔍 列出所有經節」，能一次看這個人／地在整本聖經的所有出處。', spot: 6 },
  { before: () => { try { closeCard(); } catch (e) {} }, sel: '[data-tour="verse-num"]', title: '節號＝書籤', text: '點經文的「節號」即可加入／取消書籤，加了會顯示 🔖。', spot: 4 },
  { before: () => { closeAllPanels(); openSearch(); }, beforeWait: 340,
    sel: '[data-tour="search-input"]', title: '全本搜尋', text: '在這裡打關鍵字，搜尋整本聖經（66 卷），點結果直接跳到該節。', spot: 6 },
  { before: () => { closeAllPanels(); openExplore(); }, beforeWait: 360,
    sel: '[data-tour="explore-inbook"]', title: '索引：只看本卷', text: '索引列出全部人物／地點／概念。勾「📖 只看本卷」，就只剩當前書卷出現的，瞬間從幾百個縮到幾十個。', spot: 8 },
  { before: () => { if (typeof switchExplore === 'function') switchExplore('concept'); }, beforeWait: 120,
    sel: '[data-tour="explore-cat"]', title: '索引：概念分類', text: '切到「概念」分頁，還能依分類（節期、聖所器物、寶石、度量衡…）再篩一層。', spot: 8 },
  { before: () => { closeAllPanels(); openBookMap(); }, beforeWait: 420,
    sel: '[data-tour="book-map"]', title: '本卷地圖', text: '把本卷所有地點聚成一張大地圖，點任一標記看背景資料。', spot: 6 },
  { before: () => { closeAllPanels(); openRoutes(); }, beforeWait: 480,
    sel: '[data-tour="route-picker"]', title: '路線圖', text: '亞伯拉罕遷徙、出埃及、保羅宣教…選一條，按「▶ 播放」鏡頭會跟著行程走，點停靠點看經文出處。', spot: 8 },
  { before: () => { closeAllPanels(); }, sel: '[data-tour="route-here"]', title: '本章路線提示', text: '讀到有路線經過的章節，這裡會自動浮出，點一下直接開地圖定位到該站。', spot: 6 },
  { before: () => { closeAllPanels(); openBookmarks(); }, beforeWait: 340,
    sel: '[data-tour="bookmarks-list"]', title: '我的書籤', text: '你加過書籤的經節都收在這，點任一筆跳回去繼續讀。', spot: 6 },
  { before: () => { closeAllPanels(); }, sel: '[data-tour="lineage"]', title: '世系結構圖', text: '家譜、列王的章節會出現這顆按鈕，畫出世系樹、本章人物會點亮。', spot: 6 },
  { before: () => { closeAllPanels(); }, sel: '[data-tour="sidebar"]', title: '書卷切換', text: '左側可切換書卷與章節，隨時跳到聖經任何地方。', spot: 6 },
  { before: () => { closeAllPanels(); }, sel: '[data-tour="tour-fab"]', title: '完成！你已經學會了 🎉', text: '以後忘記了不用緊張，隨時點右下角這顆「？教學導覽」，我就會再從頭帶你看一次。' },
];
function startTour() {
  // 經文內的標註與節號由伺服器產生，無法在模板上標記，這裡取第一個補上 data-tour
  [['.passage .anno', 'anno'], ['.passage .verse-num', 'verse-num']].forEach(([q, k]) => {
    document.querySelectorAll('[data-tour="' + k + '"]').forEach(el => el.removeAttribute('data-tour'));
    const el = document.querySelector(q);
    if (el) el.setAttribute('data-tour', k);
  });
  const fab = document.getElementById('tourFab');
  if (fab) fab.classList.remove('pulse');
  localStorage.setItem('bible-tour-done', '1');
  localStorage.setItem('bible-tour-last', String(Date.now()));
  SpotlightTour.start(PAGE_TOUR_STEPS, { onFinish: closeAllPanels });
}
