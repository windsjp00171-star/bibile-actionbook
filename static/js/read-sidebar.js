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
const activeBook = document.querySelector('.book-item.active');
if (activeBook) {
  const pills = activeBook.nextElementSibling;
  if (pills) pills.classList.add('open');
  activeBook.scrollIntoView({ block: 'center' });
}
