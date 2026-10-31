// ── Sidebar ──────────────────────────────────────────────────────
// 書卷搜尋：輸入關鍵字即時篩選書卷（同時套用到桌面 sidebar 與手機 drawer 兩份 nav）
function filterNavBooks(input) {
  const q = input.value.trim();
  const nav = input.closest('.sidebar, .drawer');
  if (!nav) return;
  const items = nav.querySelectorAll('.book-item');
  let matchCount = 0, firstMatch = null;
  items.forEach(item => {
    const hit = !q || item.textContent.includes(q);
    item.classList.toggle('nav-hidden', !hit);
    if (hit) { matchCount++; if (!firstMatch) firstMatch = item; }
  });
  nav.querySelectorAll('.section-label').forEach(label => {
    let sib = label.nextElementSibling, hasVisible = false;
    while (sib && !sib.classList.contains('section-label')) {
      if (sib.classList.contains('book-item') && !sib.classList.contains('nav-hidden')) hasVisible = true;
      sib = sib.nextElementSibling;
    }
    label.classList.toggle('nav-hidden', !hasVisible);
  });
  // 只剩一個符合的書卷時，自動展開章節方便直接點
  if (q && matchCount === 1 && firstMatch) {
    const pills = firstMatch.nextElementSibling;
    if (pills && pills.classList.contains('chapter-pills')) pills.classList.add('open');
  }
}

document.querySelectorAll('.book-item').forEach(el => {
  el.addEventListener('click', function(e) {
    const pills = this.nextElementSibling;
    if (!pills || !pills.classList.contains('chapter-pills')) return;
    e.preventDefault();
    pills.classList.toggle('open');
  });
});
// 展開目前書卷的章節，並把它捲到選單容器中間偏上。頁面有桌面側欄與手機抽屜兩份選單，
// 兩份各自處理（抽屜隱藏時量不到位置，改在開啟時呼叫）。只捲選單容器，不捲整個頁面。
function revealActiveInNav(nav) {
  const active = nav && nav.querySelector('.book-item.active');
  if (!active) return;
  const pills = active.nextElementSibling;
  if (pills && pills.classList.contains('chapter-pills')) pills.classList.add('open');
  // 一次算出目標位置、一次捲到（避免 scroll-behavior: smooth 讓連續兩次捲動互相干擾）
  const navTop = nav.getBoundingClientRect().top;
  let target = nav.scrollTop + active.getBoundingClientRect().top - navTop - nav.clientHeight / 3;
  // 章節很多（如詩篇）時，優先讓目前章節的按鈕可見
  const pill = nav.querySelector('.pill.active');
  if (pill) {
    const bottom = nav.scrollTop + pill.getBoundingClientRect().bottom - navTop;
    const limit = nav.clientHeight - 24;
    if (bottom - target > limit) target = bottom - limit;
  }
  nav.scrollTo({ top: Math.max(0, target), behavior: 'instant' });
}
revealActiveInNav(document.querySelector('.sidebar'));
// 字型與版面載入完成後再校正一次（先前量到的高度可能差幾個像素）；使用者已自行捲動選單就不再干預
(function () {
  const nav = document.querySelector('.sidebar');
  let touched = false;
  nav.addEventListener('wheel', () => { touched = true; }, { passive: true });
  nav.addEventListener('touchstart', () => { touched = true; }, { passive: true });
  window.addEventListener('load', () => { if (!touched) revealActiveInNav(nav); });
})();
