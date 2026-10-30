// ── 全螢幕大地圖：所有地名都標清楚 ──────────────────────────────
let _bigMap = null, _bigLayer = null;
function openBigMap() {
  if (!_curPlace) return;
  const ent = _curPlace;
  document.getElementById('bigMapTitle').textContent = '地圖　' + ent.name;
  document.getElementById('bigMapPanel').classList.add('open');
  document.getElementById('bigMapOverlay').classList.add('open');
  setTimeout(() => {
    const div = document.getElementById('bigMap');
    if (!_bigMap) {
      _bigMap = L.map(div, { zoomControl: true, attributionControl: false });
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 14 }).addTo(_bigMap);
      _bigLayer = L.layerGroup().addTo(_bigMap);
    }
    _bigLayer.clearLayers();
    const pts = [];
    Object.values(ENTITIES).forEach(e => {
      if (e.type === 'place' && e.lat != null) {
        const focus = e.name === ent.name;
        L.circleMarker([e.lat, e.lng], {
          radius: focus ? 9 : 6,
          fillColor: focus ? '#2A5C3A' : '#8B6840',
          color: '#fff', weight: 2, fillOpacity: 1
        }).bindTooltip(e.name, { permanent: true, direction: 'top',
            className: focus ? 'map-focus-label' : '' })
          .on('click', () => { if (ENTITIES[e.name]) { closeBigMap(); openCard(e.name); } })
          .addTo(_bigLayer);
        pts.push([e.lat, e.lng]);
      }
    });
    _bigMap.invalidateSize();
    if (pts.length > 1) _bigMap.fitBounds(pts, { padding: [50, 50] });
    else _bigMap.setView([ent.lat, ent.lng], 8);
  }, 80);
}
function closeBigMap() {
  document.getElementById('bigMapPanel').classList.remove('open');
  document.getElementById('bigMapOverlay').classList.remove('open');
}
