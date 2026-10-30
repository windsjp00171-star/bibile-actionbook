// ── 書籤 ────────────────────────────────────────────────────────
let _bmSet = new Set();  // 本章已加書籤的節
function _bmKey(b, c, v) { return b + '|' + c + '|' + v; }
function loadBookmarks(cb) {
  fetch('/api/bookmarks?user_id=' + encodeURIComponent(deviceId()))
    .then(r => r.json()).then(d => {
      _bmAll = d.bookmarks || [];
      _bmSet = new Set(_bmAll.filter(b => b.book_name === CUR_BOOK && b.chapter === CUR_CH)
                            .map(b => _bmKey(b.book_name, b.chapter, b.verse)));
      document.querySelectorAll('.verse').forEach(p => {
        const v = parseInt(p.dataset.v);
        p.classList.toggle('bookmarked', _bmSet.has(_bmKey(CUR_BOOK, CUR_CH, v)));
      });
      if (cb) cb();
    }).catch(() => {});
}
let _bmAll = [];
function toggleBookmark(v, p) {
  const k = _bmKey(CUR_BOOK, CUR_CH, v);
  const on = _bmSet.has(k);
  const text = p.querySelector('.verse-body').textContent;
  fetch('/api/bookmarks', {
    method: on ? 'DELETE' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: deviceId(), book: CUR_BOOK, chapter: CUR_CH, verse: v, text: text })
  }).catch(() => {});
  if (on) { _bmSet.delete(k); p.classList.remove('bookmarked'); }
  else { _bmSet.add(k); p.classList.add('bookmarked'); }
}
function openBookmarks() {
  document.getElementById('bookmarksPanel').classList.add('open');
  document.getElementById('searchOverlay').classList.add('open');
  document.getElementById('searchOverlay').onclick = closeBookmarks;
  const box = document.getElementById('bookmarksList');
  box.innerHTML = '<p class="search-empty">載入中…</p>';
  fetch('/api/bookmarks?user_id=' + encodeURIComponent(deviceId()))
    .then(r => r.json()).then(d => {
      const bms = d.bookmarks || [];
      box.innerHTML = '';
      if (!bms.length) { box.innerHTML = '<p class="search-empty">尚無書籤。點經文節號即可加入。</p>'; return; }
      bms.forEach(b => {
        const a = document.createElement('a');
        a.className = 'search-hit';
        a.href = '/read/' + encodeURIComponent(b.book_name) + '/' + b.chapter + '?v=' + b.verse;
        a.innerHTML = '<span class="hit-ref">' + b.book_name + ' ' + b.chapter + ':' + b.verse +
                      '</span><span class="hit-text">' + (b.text || '').replace(/[<>&]/g, '') + '</span>';
        box.appendChild(a);
      });
    });
}
function closeBookmarks() {
  document.getElementById('bookmarksPanel').classList.remove('open');
  document.getElementById('searchOverlay').classList.remove('open');
  document.getElementById('searchOverlay').onclick = closeSearch;
}

document.addEventListener('DOMContentLoaded', () => {
  const inp = document.getElementById('searchInput');
  if (inp) inp.addEventListener('keydown', e => { if (e.key === 'Enter') runSearch(); });
  const ef = document.getElementById('exploreFilter');
  if (ef) ef.addEventListener('input', renderExplore);
  // 節號可點以加／取消書籤
  document.querySelectorAll('.verse').forEach(p => {
    const v = parseInt(p.dataset.v);
    const num = p.querySelector('.verse-num');
    if (num) { num.style.cursor = 'pointer'; num.title = '加入／取消書籤';
      num.addEventListener('click', () => toggleBookmark(v, p)); }
    // 句末逐節回報 ⚑
    const body = p.querySelector('.verse-body');
    if (body) {
      const rb = document.createElement('button');
      rb.className = 'verse-report'; rb.textContent = '⚑';
      rb.title = '回報此節漏標／標錯';
      rb.addEventListener('click', e => { e.stopPropagation(); reportVerse(v); });
      body.appendChild(rb);
    }
  });
  loadBookmarks();
  loadRouteHere();   // 本章路線自動提示
  // 教學鈕定期脈動提醒：沒看過→提醒；看過也每隔幾天再提醒一次（功能多，容易忘）
  const TOUR_REMIND_MS = 5 * 24 * 60 * 60 * 1000;  // 5 天
  const tourLast = parseInt(localStorage.getItem('bible-tour-last') || '0', 10);
  if (Date.now() - tourLast > TOUR_REMIND_MS) {
    const fab = document.getElementById('tourFab');
    if (fab) fab.classList.add('pulse');
  }
  // 從搜尋結果跳轉而來：高亮並捲到該節
  const v = new URLSearchParams(location.search).get('v');
  if (v) {
    const el = document.querySelector('.verse[data-v="' + v + '"]') ||
               [...document.querySelectorAll('.verse-num')].find(n => n.textContent.trim() === v)?.closest('.verse');
    if (el) { el.classList.add('verse-hl'); el.scrollIntoView({block:'center'}); }
  }
});

function renderRelations(name) {
  const box = document.getElementById('cardRelations');
  box.innerHTML = '';
  const rel = RELATIONS[name];
  if (!rel) return;
  const seen = REL_ORDER.filter(r => rel[r]);
  const rest = Object.keys(rel).filter(r => !REL_ORDER.includes(r));
  [...seen, ...rest].forEach(relType => {
    const row = document.createElement('div');
    row.className = 'rel-row';
    const lbl = document.createElement('span');
    lbl.className = 'rel-label';
    lbl.textContent = relType;
    row.appendChild(lbl);
    rel[relType].forEach(target => {
      if (!_lookupEntity(target)) return;
      const chip = document.createElement('span');
      chip.className = 'rel-chip';
      const t = _lookupEntity(target);
      chip.textContent = (t && t.name) ? t.name : target;
      chip.addEventListener('click', e => { e.stopPropagation(); openCard(target); });
      row.appendChild(chip);
    });
    box.appendChild(row);
  });
}

function _esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
function openCard(name) {
  const ent = _lookupEntity(name);
  if (!ent) return;
  _curEntity = name;
  document.getElementById('cardBadge').textContent = TYPE_LABEL[ent.type] || '';
  document.getElementById('cardBadge').className = 'card-badge anno-' + ent.type;
  if (ent.type === 'place' && ent.lat != null) {
    document.getElementById('cardBadge').innerHTML += ' <span class="map-avail" title="有地圖座標">📍地圖</span>';
  }
  document.getElementById('cardName').innerHTML = _esc(ent.name) +
    (ent.reading ? ' <span class="card-reading">' + _esc(ent.reading) + '</span>' : '') +
    (ent.name_en ? '<span class="card-en">　' + _esc(ent.name_en) + '</span>' : '');
  document.getElementById('cardDesc').textContent = ent.desc || '';
  renderRelations(name);
  const vbox = document.getElementById('cardVerses');
  vbox.innerHTML = '';
  (ent.verses || '').split('、').filter(Boolean).forEach(v => {
    const chip = document.createElement('span');
    chip.className = 'verse-chip';
    chip.textContent = v;
    vbox.appendChild(chip);
  });
  renderMap(ent);
  // 重置「標註有誤」按鈕（每張卡片都要能回報）
  document.getElementById('cardFeedbackBtn').style.display = '';
  document.getElementById('cardFeedbackDone').style.display = 'none';
  document.getElementById('annoCard').classList.add('open');
  document.getElementById('cardOverlay').classList.add('open');
}

document.querySelectorAll('.anno').forEach(el => {
  el.addEventListener('click', e => { e.stopPropagation(); openCard(el.dataset.entity); });
});
