const TYPE_LABEL = { person: '人物', place: '地點', concept: '族群／概念' };
// 關係顯示順序與標籤
const REL_ORDER = ['父母','母','子女','手足','配偶','師長','門生','同工','敵對','主','婢女','臣僕','祖父','孫'];

// ── Font size ───────────────────────────────────────────────────
let fontSize = parseInt(localStorage.getItem('bible-fs') || '18');
applyFont();
function applyFont() {
  document.getElementById('passage').style.fontSize = fontSize + 'px';
  localStorage.setItem('bible-fs', fontSize);
}
function setFont(delta) {
  fontSize = Math.max(14, Math.min(26, fontSize + delta));
  applyFont();
}

// ── Drawer ──────────────────────────────────────────────────────
function openDrawer() {
  document.getElementById('drawer').classList.add('open');
  document.getElementById('overlay').classList.add('open');
  if (typeof revealActiveInNav === 'function') revealActiveInNav(document.getElementById('drawer'));
}
function closeDrawer() {
  document.getElementById('drawer').classList.remove('open');
  document.getElementById('overlay').classList.remove('open');
}

function toggleNav() {
  var collapsed = document.body.classList.toggle('nav-collapsed');
  var btn = document.getElementById('navToggle');
  btn.textContent = collapsed ? '\u203a' : '\u2039';
  btn.setAttribute('aria-label', collapsed ? '\u5c55\u958b\u66f8\u5377\u9078\u55ae' : '\u6536\u5408\u66f8\u5377\u9078\u55ae');
  btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
  try { localStorage.setItem('bible-nav-collapsed', collapsed ? '1' : '0'); } catch (e) {}
}

// 重新整理後讓按鈕箭頭方向跟已還原的狀態一致
(function () {
  if (document.body.classList.contains('nav-collapsed')) {
    var btn = document.getElementById('navToggle');
    btn.textContent = '\u203a';
    btn.setAttribute('aria-label', '\u5c55\u958b\u66f8\u5377\u9078\u55ae');
    btn.setAttribute('aria-expanded', 'false');
  }
})();

// ── Anno card ───────────────────────────────────────────────────
let _map = null, _layer = null;

function closeCard() {
  document.getElementById('annoCard').classList.remove('open');
  document.getElementById('cardOverlay').classList.remove('open');
}

let _curPlace = null;
function renderMap(ent) {
  const wrap = document.getElementById('cardMap');
  const outer = document.getElementById('cardMapWrap');
  if (ent.type !== 'place' || ent.lat == null) { outer.style.display = 'none'; _curPlace = null; return; }
  outer.style.display = 'block';
  _curPlace = ent;
  if (!_map) {
    _map = L.map(wrap, { zoomControl: true, attributionControl: false });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 14 }).addTo(_map);
    _layer = L.layerGroup().addTo(_map);
  }
  _layer.clearLayers();
  // 其他地名：只放小點，名稱改成碰觸/點擊才顯示，避免標籤全擠在一起；點了可開該地卡片
  Object.values(ENTITIES).forEach(e => {
    if (e.type === 'place' && e.name !== ent.name && e.lat != null) {
      L.circleMarker([e.lat, e.lng], { radius: 5, fillColor: '#8B6840', color: '#fff', weight: 1.5, fillOpacity: 1 })
        .bindTooltip(e.name, { direction: 'top', opacity: 0.95 })
        .on('click', () => { if (ENTITIES[e.name]) openCard(e.name); })
        .addTo(_layer);
    }
  });
  // 焦點地名：較大、固定標籤
  L.circleMarker([ent.lat, ent.lng], { radius: 8, fillColor: '#2A5C3A', color: '#fff', weight: 2, fillOpacity: 1 })
    .bindTooltip(ent.name, { permanent: true, direction: 'top', className: 'map-focus-label' }).addTo(_layer);
  _map.setView([ent.lat, ent.lng], 7);
  setTimeout(() => { _map.invalidateSize(); _map.flyTo([ent.lat, ent.lng], 7); }, 60);
}

function _lookupEntity(name) {
  return ENTITIES[name] || RELATED_BRIEF[name] || null;
}
