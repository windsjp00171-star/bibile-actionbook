// ── 本卷地圖 ────────────────────────────────────────────────────
let _bookMap = null;
function openBookMap() {
  document.getElementById('bookMapPanel').classList.add('open');
  document.getElementById('bookMapOverlay').classList.add('open');
  fetch('/api/book_places?book=' + encodeURIComponent(CUR_BOOK)).then(r => r.json()).then(d => {
    setTimeout(() => {
      const el = document.getElementById('bookMap');
      if (!_bookMap) {
        _bookMap = L.map(el, { zoomControl: true, attributionControl: false });
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 16 }).addTo(_bookMap);
      }
      _bookMap.eachLayer(l => { if (l instanceof L.CircleMarker) _bookMap.removeLayer(l); });
      const pts = [];
      const markers = {};   // key -> marker，供清單點擊時定位、開 popup
      const popupHtml = (p) => '<div class="map-popup">' +
        '<b>' + _esc(p.name) + '</b>' +
        (p.desc ? '<p>' + _esc(p.desc) + '</p>' : '') +
        (ENTITIES[p.key] || RELATED_BRIEF[p.key]
          ? '<a href="javascript:void(0)" onclick="closeBookMap();openCard(\'' + p.key.replace(/'/g, "\\'") + '\')">查看完整資料 →</a>' : '') +
        '</div>';
      // 座標很接近的點會在縮小檢視時疊在一起、擋住彼此無法點擊，先把重複／極接近的點錯開
      const seen = {};
      (d.places || []).forEach(p => {
        const key = p.lat.toFixed(2) + ',' + p.lng.toFixed(2);
        const n = seen[key] || 0; seen[key] = n + 1;
        const lat = n === 0 ? p.lat : p.lat + 0.045 * n;
        const lng = n === 0 ? p.lng : p.lng + 0.03 * n;
        // 常駐標籤在地點多時會整片疊字看不清、擋住彼此，改用滑過才顯示；
        // 點圖標／清單直接彈出 popup 顯示簡介，不整個跳走離開地圖
        const marker = L.circleMarker([lat, lng], { radius: 6, fillColor: '#8B6840', color: '#fff', weight: 1.5, fillOpacity: 1 })
          .bindTooltip(p.name, { direction: 'top' })
          .bindPopup(popupHtml(p))
          .addTo(_bookMap);
        markers[p.key] = { marker, lat, lng };
        pts.push([lat, lng]);
      });
      _bookMap.invalidateSize();
      if (pts.length > 1) _bookMap.fitBounds(pts, { padding: [40, 40] });
      else if (pts.length === 1) _bookMap.setView(pts[0], 7);
      else _bookMap.setView([31.5, 35], 6);
      // 點清單：地圖定位過去＋直接彈出資訊 popup，停留在地圖上，不跳走
      const focusFromKey = (key) => {
        const m = markers[key];
        if (!m) return;
        _bookMap.panTo([m.lat, m.lng], { animate: true });
        m.marker.openPopup();
      };
      renderBookMapList(d.places || [], focusFromKey);
    }, 80);
  });
}
function renderBookMapList(places, focusFromKey) {
  const box = document.getElementById('bookMapList');
  if (!box) return;
  box.innerHTML = '';
  places.slice().sort((a, b) => a.name.localeCompare(b.name, 'zh-Hant')).forEach(p => {
    const row = document.createElement('div');
    row.className = 'place-item';
    row.textContent = p.name;
    row.onclick = () => focusFromKey(p.key);
    box.appendChild(row);
  });
}
function closeBookMap() {
  document.getElementById('bookMapPanel').classList.remove('open');
  document.getElementById('bookMapOverlay').classList.remove('open');
}

// ── 聖經路線圖 ──────────────────────────────────────────────────
let _routeMap = null, _routeLayers = [], _routesList = null, _curRoute = null, _routeAnim = null;
function openRoutes() {
  document.getElementById('routesPanel').classList.add('open');
  document.getElementById('routesOverlay').classList.add('open');
  fetch('/api/routes?book=' + encodeURIComponent(CUR_BOOK)).then(r => r.json()).then(d => {
    _routesList = d.routes || [];
    if (!_routesList.length) {
      document.getElementById('routePicker').innerHTML = '<span class="route-empty">尚無路線資料。</span>';
      return;
    }
    _routesExpanded = false;       // 預設只顯示本卷相關路線
    renderRoutePicker();
    if (_pendingRoute) {           // 由「本章路線」提示點入：開到指定路線/站
      const pr = _pendingRoute; _pendingRoute = null;
      if (!_routesList.some(r => r.relevant && r.id === pr.id)) { _routesExpanded = true; renderRoutePicker(); }
      selectRoute(pr.id, pr.stop);
      const chip = document.querySelector('#routePicker .route-chip[data-rid="' + pr.id + '"]');
      if (chip) highlightChip(chip);
    } else {
      // 預設選第一條（情境相關優先，已由後端排序）
      selectRoute(_routesList[0].id);
    }
  });
}
// 從「本章路線」提示開啟，定位到指定站
let _pendingRoute = null;
function openRoutesAt(id, stop) { _pendingRoute = { id: id, stop: stop }; openRoutes(); }
// 讀經頁載入時：自動偵測本章經過的路線，浮出提示條
function loadRouteHere() {
  const bar = document.getElementById('routeHereBar');
  if (!bar) return;
  fetch('/api/routes_here?book=' + encodeURIComponent(CUR_BOOK) + '&chapter=' + CUR_CH)
    .then(r => r.json()).then(d => {
      const hits = d.here || [];
      if (!hits.length) { bar.style.display = 'none'; return; }
      // 依路線分組，取本章第一個站
      const byRoute = {};
      hits.forEach(h => { if (!byRoute[h.id]) byRoute[h.id] = { route: h.route, color: h.color, stops: [], first: h.stop }; byRoute[h.id].stops.push(h.name); });
      bar.innerHTML = '<span class="rh-label">🧭 本章路線</span>' +
        Object.keys(byRoute).map(id => {
          const g = byRoute[id];
          const txt = g.stops.length > 1 ? (g.stops[0] + ' 等 ' + g.stops.length + ' 站') : g.stops[0];
          return '<button class="rh-chip" style="--rc:' + g.color + '" onclick="openRoutesAt(\'' + id + '\',' + g.first + ')">' +
                 g.route + ' · ' + txt + '</button>';
        }).join('');
      bar.style.display = 'flex';
    }).catch(() => { bar.style.display = 'none'; });
}
let _routesExpanded = false;
function renderRoutePicker() {
  const pick = document.getElementById('routePicker');
  pick.innerHTML = '';
  const relevant = _routesList.filter(r => r.relevant);
  const others = _routesList.filter(r => !r.relevant);
  // 有相關路線時預設只顯示相關；無相關（如讀的卷沒對應路線）則全顯示
  const baseList = (relevant.length && !_routesExpanded) ? relevant : _routesList;
  let firstChip = null;
  baseList.forEach(r => {
    const b = document.createElement('button');
    b.className = 'route-chip' + (r.relevant ? ' relevant' : '');
    b.style.setProperty('--rc', r.color);
    b.textContent = (r.relevant ? '✦ ' : '') + r.name;
    b.dataset.rid = r.id;
    b.onclick = () => { selectRoute(r.id); highlightChip(b); };
    pick.appendChild(b);
    if (!firstChip) firstChip = b;
  });
  // 「顯示其他路線 / 收起」切換
  if (relevant.length && others.length) {
    const t = document.createElement('button');
    t.className = 'route-toggle';
    t.textContent = _routesExpanded ? '收起其他路線' : ('＋ 其他路線 (' + others.length + ')');
    t.onclick = () => { _routesExpanded = !_routesExpanded; renderRoutePicker(); restoreActiveChip(); };
    pick.appendChild(t);
  }
  if (firstChip && !document.querySelector('#routePicker .route-chip.active')) highlightChip(firstChip);
}
function restoreActiveChip() {
  if (!_curRoute) return;
  const el = document.querySelector('#routePicker .route-chip[data-rid="' + _curRoute.id + '"]');
  if (el) highlightChip(el);
}
function highlightChip(el) {
  document.querySelectorAll('#routePicker .route-chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
}
function selectRoute(id, focusStop) {
  _stopAnim();   // 切換路線前先徹底停掉舊路線可能還在跑的動畫，否則新路線按播放會整個靜默不動
  fetch('/api/routes?id=' + encodeURIComponent(id)).then(r => r.json()).then(rt => {
    _curRoute = rt;
    document.getElementById('routeInfo').innerHTML =
      '<div class="route-headline"><div class="route-name">' + rt.name + '</div>' +
      '<div class="route-ctrl">' +
        '<button class="route-play" id="routePlay" onclick="togglePlay()">▶ 播放</button>' +
        '<select class="route-speed" id="routeSpeed" onchange="_routeSpeed=parseFloat(this.value)">' +
          '<option value="1.6">0.6×</option><option value="1" selected>1×</option>' +
          '<option value="0.6">1.6×</option><option value="0.35">3×</option>' +
        '</select>' +
      '</div></div>' +
      '<div class="route-ref">' + (rt.ref || '') + '</div>' +
      (rt.summary ? '<div class="route-sum">' + rt.summary + '</div>' : '');
    drawRoute(rt);
    renderStops(rt);
    // 由「本章路線」提示開入時，定位並標示該站
    if (focusStop && rt.waypoints && rt.waypoints[focusStop - 1]) {
      const w = rt.waypoints[focusStop - 1];
      setTimeout(() => { if (_routeMap) { _routeMap.setView([w.lat, w.lng], 8); _highlightStopRow(focusStop - 1); } }, 200);
    }
  });
}
function _highlightStopRow(idx) {
  const rows = document.querySelectorAll('#routeStops .route-stop');
  rows.forEach((r, i) => r.classList.toggle('rs-focus', i === idx));
  if (rows[idx]) rows[idx].scrollIntoView({ block: 'nearest' });
}
function _ensureRouteMap() {
  const el = document.getElementById('routeMap');
  if (!_routeMap) {
    _routeMap = L.map(el, { zoomControl: true, attributionControl: false });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 16 }).addTo(_routeMap);
  }
  return _routeMap;
}
function _clearRoute() {
  if (_routeAnim) { cancelAnimationFrame(_routeAnim); _routeAnim = null; }
  if (_routeTimer) { clearTimeout(_routeTimer); _routeTimer = null; }
  _routeLayers.forEach(l => _routeMap.removeLayer(l));
  _routeLayers = [];
}
// 重複停靠點（往返同地）稍微錯開，避免編號標記疊在一起
function _dispPositions(wps) {
  const seen = {}, out = [];
  wps.forEach(w => {
    const key = w.lat.toFixed(3) + ',' + w.lng.toFixed(3);
    const n = seen[key] || 0; seen[key] = n + 1;
    if (n === 0) out.push([w.lat, w.lng]);
    else out.push([w.lat + 0.07 * n, w.lng + 0.05 * n]);  // 第 n 次重複往東北錯開
  });
  return out;
}
function _routeMarker(rt, w, i, pos) {
  const ll = pos || [w.lat, w.lng];
  const icon = L.divIcon({ className: 'route-num-icon',
    html: '<span style="background:' + rt.color + '">' + (i + 1) + '</span>',
    iconSize: [22, 22], iconAnchor: [11, 11] });
  return L.marker(ll, { icon })
    .bindTooltip(w.name, { permanent: true, direction: 'top', offset: [0, -10] })
    .bindPopup(_stopPopupHtml(w, i));
}
// 停靠點彈窗：地名 + 經文連結 + 說明
function _stopPopupHtml(w, i) {
  const nav = _parseRef(w.ref);
  const refHtml = nav
    ? '<a href="/read/' + encodeURIComponent(nav.book) + '/' + nav.ch +
      (nav.v ? '?v=' + nav.v : '') + '" class="rp-link">' + w.ref + ' →</a>'
    : (w.ref || '');
  return '<b>' + (i + 1) + '. ' + w.name + '</b><br>' + refHtml + (w.note ? '<br>' + w.note : '');
}
// 經文簡稱 → 全名（路線資料 ref 用簡稱）
const _BOOK_ABBR = {
  '創': '創世記', '出': '出埃及記', '利': '利未記', '民': '民數記', '申': '申命記',
  '書': '約書亞記', '士': '士師記', '得': '路得記', '撒上': '撒母耳記上', '撒下': '撒母耳記下',
  '王上': '列王紀上', '王下': '列王紀下', '拉': '以斯拉記', '尼': '尼希米記', '詩': '詩篇',
  '賽': '以賽亞書', '耶': '耶利米書', '結': '以西結書', '但': '但以理書',
  '太': '馬太福音', '可': '馬可福音', '路': '路加福音', '約': '約翰福音', '徒': '使徒行傳'
};
function _parseRef(ref) {
  if (!ref) return null;
  const m = ref.match(/^([一-龥]+?(?:上|下)?)(\d+):(\d+)/);
  if (!m) return null;
  // 先試 2 字簡稱（王上/王下/撒上…）再試 1 字
  let pre = m[1], book = _BOOK_ABBR[pre];
  if (!book && pre.length > 1) book = _BOOK_ABBR[pre.slice(0, 1)];
  if (!book) return null;
  return { book: book, ch: parseInt(m[2]), v: parseInt(m[3]) };
}
// 方向箭頭：在每段中點放一個依方位角旋轉的箭頭
function _arrowMarkers(rt) {
  const out = [];
  const wps = rt.waypoints || [];
  for (let i = 0; i < wps.length - 1; i++) {
    const a = wps[i], b = wps[i + 1];
    if (a.lat === b.lat && a.lng === b.lng) continue;
    const mid = [(a.lat + b.lat) / 2, (a.lng + b.lng) / 2];
    const ang = Math.atan2(b.lng - a.lng, b.lat - a.lat) * 180 / Math.PI; // 0=北，順時針
    const icon = L.divIcon({ className: 'route-arrow-icon',
      html: '<span style="color:' + rt.color + ';transform:rotate(' + ang + 'deg)">▲</span>',
      iconSize: [16, 16], iconAnchor: [8, 8] });
    out.push(L.marker(mid, { icon, interactive: false }));
  }
  return out;
}
// 靜態：一次畫完整條路線（含方向箭頭）
function drawRoute(rt) {
  setTimeout(() => {
    _ensureRouteMap();
    _clearRoute();
    const pts = (rt.waypoints || []).map(w => [w.lat, w.lng]);
    const disp = _dispPositions(rt.waypoints || []);
    if (pts.length > 1) {
      const line = L.polyline(pts, { color: rt.color, weight: 3, opacity: 0.85, dashArray: '6,7' }).addTo(_routeMap);
      _routeLayers.push(line);
      _arrowMarkers(rt).forEach(a => { a.addTo(_routeMap); _routeLayers.push(a); });
    }
    (rt.waypoints || []).forEach((w, i) => { const m = _routeMarker(rt, w, i, disp[i]).addTo(_routeMap); _routeLayers.push(m); });
    _routeMap.invalidateSize();
    if (pts.length > 1) _routeMap.fitBounds(pts, { padding: [45, 45] });
    else if (pts.length === 1) _routeMap.setView(pts[0], 7);
  }, 80);
}
// 播放／暫停切換
function togglePlay() {
  if (_routePlaying && !_routePaused) { pauseRoute(); }
  else if (_routePlaying && _routePaused) { resumeRoute(); }
  else { playRoute(); }
}
function _setPlayBtn(txt) { const b = document.getElementById('routePlay'); if (b) b.textContent = txt; }
// 完全停止動畫（不同於暫停：暫停後按播放要能接續，這裡是「切換路線」時要徹底歸零，
// 不然切到新路線後 _routePlaying 還殘留 true，按播放會誤觸發成「暫停」而整個不動）
function _stopAnim() {
  if (_routeAnim) { cancelAnimationFrame(_routeAnim); _routeAnim = null; }
  if (_routeTimer) { clearTimeout(_routeTimer); _routeTimer = null; }
  _routePlaying = false; _routePaused = false; _anim = null;
  _setPlayBtn('▶ 播放');
}
function pauseRoute() {
  _routePaused = true;
  if (_routeAnim) { cancelAnimationFrame(_routeAnim); _routeAnim = null; }
  if (_routeTimer) { clearTimeout(_routeTimer); _routeTimer = null; }
  _setPlayBtn('▶ 繼續');
}
function resumeRoute() {
  if (!_routePaused) return;
  _routePaused = false;
  _setPlayBtn('⏸ 暫停');
  _routeTick();   // 從目前進度接續
}
// 動畫狀態（讓暫停/速度能接續）
let _routePlaying = false, _routePaused = false, _routeTimer = null, _routeSpeed = 1;
let _anim = null;  // { wps, allPts, line, drawn, seg, segStart, paused }
function playRoute() {
  const rt = _curRoute;
  if (!rt || !rt.waypoints || rt.waypoints.length < 2) return;
  _ensureRouteMap();
  _clearRoute();
  _routeMap.invalidateSize();
  const wps = rt.waypoints;
  const allPts = wps.map(w => [w.lat, w.lng]);
  // 縮放全程固定不變（只算一次能容下整條路線的縮放等級），圖磚只需在這個
  // 解析度載入一次；鏡頭仍會平移跟著走保留移動感——放大縮小才是最容易讓
  // 圖磚被打斷重載而閃爍/空白的操作，單純平移 Leaflet 本來就處理得平順
  const fixedZoom = _routeMap.getBoundsZoom(L.latLngBounds(allPts), false, [45, 45]);
  _routeMap.setView(allPts[0], fixedZoom, { animate: false });
  const disp = _dispPositions(wps);
  const line = L.polyline([], { color: rt.color, weight: 4, opacity: 0.95 }).addTo(_routeMap);
  _routeLayers.push(line);
  const traveler = L.circleMarker(allPts[0], { radius: 7, fillColor: '#fff', color: rt.color, weight: 3, fillOpacity: 1 }).addTo(_routeMap);
  _routeLayers.push(traveler);
  const m0 = _routeMarker(rt, wps[0], 0, disp[0]).addTo(_routeMap); _routeLayers.push(m0);
  _anim = { rt, wps, disp, allPts, line, traveler,
            drawn: [[wps[0].lat, wps[0].lng]], seg: 0, segT0: 0, elapsed: 0 };
  _routePlaying = true; _routePaused = false;
  _setPlayBtn('⏸ 暫停');
  _routeTick();
}
const _SEG_BASE = 900;  // 每段基準毫秒（再乘速度倍率）
function _routeTick() {
  const A = _anim; if (!A) return;
  if (A.seg >= A.wps.length - 1) {       // 播完，視角本來就沒動過，不用再飛回去
    _routePlaying = false; _routePaused = false;
    _setPlayBtn('▶ 重新播放');
    return;
  }
  const a = A.wps[A.seg], b = A.wps[A.seg + 1];
  const dur = _SEG_BASE * _routeSpeed;
  const start = performance.now() - A.elapsed;   // 接續已過時間（暫停用）
  function step(now) {
    if (_routePaused) { A.elapsed = now - start; return; }
    const t = Math.min(1, (now - start) / dur);
    const e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    const lat = a.lat + (b.lat - a.lat) * e, lng = a.lng + (b.lng - a.lng) * e;
    A.line.setLatLngs(A.drawn.concat([[lat, lng]]));
    A.traveler.setLatLng([lat, lng]);
    // 鏡頭平移跟著目前位置走，縮放全程固定（見 playRoute 算好的 fixedZoom）不再變動，
    // 純平移 Leaflet 處理得平順不會讓圖磚被打斷重載
    _routeMap.panTo([lat, lng], { animate: false });
    if (t < 1) { _routeAnim = requestAnimationFrame(step); }
    else {
      A.drawn.push([b.lat, b.lng]);
      // 段末補上方向箭頭與停靠點
      const ar = _arrowMarkers({ color: A.rt.color, waypoints: [a, b] })[0];
      if (ar) { ar.addTo(_routeMap); _routeLayers.push(ar); }
      const m = _routeMarker(A.rt, b, A.seg + 1, A.disp[A.seg + 1]).addTo(_routeMap); _routeLayers.push(m);
      A.seg++; A.elapsed = 0;
      _routeTimer = setTimeout(_routeTick, 240 * _routeSpeed);
    }
  }
  _routeAnim = requestAnimationFrame(step);
}
function renderStops(rt) {
  const box = document.getElementById('routeStops');
  box.innerHTML = '';
  (rt.waypoints || []).forEach((w, i) => {
    const nav = _parseRef(w.ref);
    const row = document.createElement('div');
    row.className = 'route-stop';
    row.innerHTML = '<span class="rs-num" style="background:' + rt.color + '">' + (i + 1) + '</span>' +
      '<span class="rs-body"><b>' + w.name + '</b> ' +
        (nav ? '<a class="rs-ref rs-link" href="/read/' + encodeURIComponent(nav.book) + '/' + nav.ch +
               (nav.v ? '?v=' + nav.v : '') + '" onclick="event.stopPropagation()">' + w.ref + ' →</a>'
             : '<span class="rs-ref">' + (w.ref || '') + '</span>') +
        (w.note ? '<br><span class="rs-note">' + w.note + '</span>' : '') + '</span>';
    row.onclick = () => { if (_routeMap) { _routeMap.setView([w.lat, w.lng], 8); } };
    box.appendChild(row);
  });
}
function closeRoutes() {
  document.getElementById('routesPanel').classList.remove('open');
  document.getElementById('routesOverlay').classList.remove('open');
}
