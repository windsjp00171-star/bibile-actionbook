// ── 經文搜尋 ──────────────────────────────────────────────────────
function openSearch() {
  document.getElementById('searchPanel').classList.add('open');
  document.getElementById('searchOverlay').classList.add('open');
  setTimeout(() => document.getElementById('searchInput').focus(), 80);
}
function closeSearch() {
  document.getElementById('searchPanel').classList.remove('open');
  document.getElementById('searchOverlay').classList.remove('open');
}
function _hl(text, q) {
  const i = text.indexOf(q);
  if (i < 0) return text.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  const esc = s => s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  return esc(text.slice(0, i)) + '<mark>' + esc(q) + '</mark>' + esc(text.slice(i + q.length));
}
function runSearch() {
  const q = document.getElementById('searchInput').value.trim();
  const meta = document.getElementById('searchMeta');
  const box = document.getElementById('searchResults');
  if (!q) { meta.textContent = ''; box.innerHTML = ''; return; }
  meta.textContent = '搜尋中…'; box.innerHTML = '';
  const scoped = document.getElementById('searchScope').checked;
  const bookParam = scoped ? '&book=' + encodeURIComponent(CUR_BOOK) : '';
  fetch('/api/search?q=' + encodeURIComponent(q) + bookParam + '&limit=200')
    .then(r => r.json()).then(d => {
      meta.textContent = '找到 ' + d.total + ' 節' + (d.truncated ? '（顯示前 200）' : '');
      box.innerHTML = '';
      d.results.forEach(r => {
        const a = document.createElement('a');
        a.className = 'search-hit';
        a.href = '/read/' + encodeURIComponent(r.book) + '/' + r.chapter + '?v=' + r.verse;
        a.innerHTML = '<span class="hit-ref">' + r.book + ' ' + r.chapter + ':' + r.verse +
                      '</span><span class="hit-text">' + _hl(r.text, q) + '</span>';
        box.appendChild(a);
      });
      if (!d.results.length) box.innerHTML = '<p class="search-empty">查無符合的經文。</p>';
    }).catch(() => { meta.textContent = '搜尋失敗，請稍後再試。'; });
}
// ── 人物/地點/概念索引 ──────────────────────────────────────────
let _exploreData = null, _exploreType = 'person';
function openExplore() {
  document.getElementById('explorePanel').classList.add('open');
  document.getElementById('searchOverlay').classList.add('open');
  document.getElementById('searchOverlay').onclick = closeExplore;
  if (_exploreData) { renderExplore(); }
  else fetch('/api/entities?book=' + encodeURIComponent(CUR_BOOK)).then(r => r.json())
    .then(d => { _exploreData = d; updateExploreCounts(); renderExplore(); });
}
function updateExploreCounts() {
  if (!_exploreData) return;
  ['person', 'place', 'concept'].forEach(t => {
    const el = document.getElementById('cnt-' + t);
    if (el) el.textContent = (_exploreData[t] || []).length;
  });
}
function closeExplore() {
  document.getElementById('explorePanel').classList.remove('open');
  document.getElementById('searchOverlay').classList.remove('open');
  document.getElementById('searchOverlay').onclick = closeSearch;
}
// 索引點擊 → 先取詞條卡片資料，開卡片看標註內容（非直接跑搜尋）
function openEntityInfo(key) {
  fetch('/api/entity?name=' + encodeURIComponent(key)).then(r => r.json()).then(c => {
    if (c.error) return;
    RELATED_BRIEF[key] = c;
    closeExplore();
    openCard(key);
  }).catch(() => {});
}
// 在卡片列出此詞條的所有經節（去掉括號註記再搜）
function listEntityVerses() {
  if (!_curEntity) return;
  const term = _curEntity.replace(/（.*$/, '').replace(/\(.*$/, '');
  closeCard();
  openSearch();
  document.getElementById('searchInput').value = term;
  document.getElementById('searchScope').checked = false;
  runSearch();
}
function switchExplore(t) {
  _exploreType = t;
  document.querySelectorAll('.explore-tab').forEach(b => b.classList.toggle('active', b.dataset.type === t));
  // 分類下拉只在概念分頁出現
  const catSel = document.getElementById('exploreCat');
  if (catSel) { catSel.style.display = (t === 'concept') ? '' : 'none'; if (t !== 'concept') catSel.value = ''; }
  renderExplore();
}
function renderExplore() {
  if (!_exploreData) return;
  const filter = document.getElementById('exploreFilter').value.trim();
  const testVal = (document.getElementById('exploreTestament') || {}).value || '';
  const catVal = (document.getElementById('exploreCat') || {}).value || '';
  const inBook = (document.getElementById('exploreInBook') || {}).checked || false;
  const list = document.getElementById('exploreList');
  list.innerHTML = '';
  const lcFilter = filter.toLowerCase();
  const rows = (_exploreData[_exploreType] || []).filter(e => {
    if (filter && !e.name.includes(filter) && !(e.name_en || '').toLowerCase().includes(lcFilter)) return false;
    if (testVal && e.testament !== testVal && e.testament !== 'both') return false;
    if (catVal && e.cat !== catVal) return false;
    if (inBook && !e.in_book) return false;
    return true;
  });
  rows.forEach(e => {
    const a = document.createElement('button');
    a.className = 'explore-item';
    a.innerHTML = (e.has_map ? '📍 ' : '') + e.name + (e.name_en ? ' <span class="ex-en">' + e.name_en + '</span>' : '');
    a.onclick = () => openEntityInfo(e.key);
    list.appendChild(a);
  });
  const shown = document.getElementById('exploreShown');
  if (shown) shown.textContent = rows.length ? ('共 ' + rows.length + ' 筆') : '無符合';
}
