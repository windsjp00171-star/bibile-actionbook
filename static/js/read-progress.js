// ── Reading progress (localStorage, offline-friendly) ───────────

function loadProgress() {
  try { return JSON.parse(localStorage.getItem('bible-progress') || '{}'); }
  catch (e) { return {}; }
}
function saveProgress(p) { localStorage.setItem('bible-progress', JSON.stringify(p)); }

// 記錄目前章節為「最後閱讀」並標記已讀
const _prog = loadProgress();
_prog.last = { book: CUR_BOOK, chapter: CUR_CH };
_prog.read = _prog.read || {};
_prog.read[CUR_BOOK] = _prog.read[CUR_BOOK] || [];
if (!_prog.read[CUR_BOOK].includes(CUR_CH)) {
  _prog.read[CUR_BOOK].push(CUR_CH);
  _prog.read[CUR_BOOK].sort((a, b) => a - b);
}
saveProgress(_prog);

// 同步存檔到 Supabase（首頁存檔選單用）。無登入，以裝置 ID 識別。
function deviceId() {
  let id = localStorage.getItem('bible-device-id');
  if (!id) {
    id = (crypto.randomUUID ? crypto.randomUUID()
          : 'dev-' + Date.now() + '-' + Math.random().toString(16).slice(2));
    localStorage.setItem('bible-device-id', id);
  }
  return id;
}
fetch('/api/progress', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ user_id: deviceId(), book: CUR_BOOK, chapter: CUR_CH })
}).catch(() => {});

// 在側欄已讀章節的 pill 加標記，書卷顯示讀過幾章
function markRead(root) {
  const read = _prog.read || {};
  root.querySelectorAll('.book-item').forEach(item => {
    const name = item.textContent.trim();
    const list = read[name] || [];
    if (list.length) {
      const badge = document.createElement('span');
      badge.className = 'read-count';
      badge.textContent = list.length;
      item.appendChild(badge);
    }
    const pills = item.nextElementSibling;
    if (pills && pills.classList.contains('chapter-pills')) {
      pills.querySelectorAll('.pill').forEach(pill => {
        if (list.includes(parseInt(pill.textContent))) pill.classList.add('read');
      });
    }
  });
}
document.querySelectorAll('.sidebar, .drawer').forEach(markRead);

// ── 標註回報 ────────────────────────────────────────────────
let _curEntity = '';  // 目前開著的實體名稱

function submitFeedback() {
  if (!_curEntity) return;
  document.getElementById('cardFeedbackBtn').style.display = 'none';
  fetch('/api/feedback', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({entity: _curEntity, book: CUR_BOOK, chapter: CUR_CH})
  }).finally(() => {
    document.getElementById('cardFeedbackDone').style.display = 'block';
  });
}

// 章節層級回報：可回報「漏標」（沒有卡片可按的詞）或整章問題
// 逐節回報：點某節的 ⚑ 回報「漏標／標錯」，精確到該節
function reportVerse(v) {
  const note = prompt('回報第 ' + v + ' 節的標註問題（例如：「迦瑪列」沒標、「某詞」標錯人）：');
  if (!note || !note.trim()) return;
  fetch('/api/feedback', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({entity: '（逐節回報）', book: CUR_BOOK, chapter: CUR_CH, verse: v, note: note.trim()})
  }).finally(() => alert('已回報第 ' + v + ' 節，謝謝！'));
}

// 滑動切換章節已移除——垂直捲動易誤觸翻章。改用底部「上一章／下一章」按鈕。
