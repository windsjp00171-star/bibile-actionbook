// ── 本章世系結構圖（SVG） ──────────────────────────────────────
function renderLineage() {
  if (!LINEAGE) return;
  const svg = document.getElementById('lineageSvg');
  const SVGNS = 'http://www.w3.org/2000/svg';
  svg.innerHTML = '';
  // 依代分列
  const byGen = {};
  LINEAGE.nodes.forEach(n => { (byGen[n.gen] = byGen[n.gen] || []).push(n); });
  const gens = Object.keys(byGen).map(Number).sort((a, b) => a - b);
  const NW = 96, NH = 34, GAPX = 18, GAPY = 56;
  const maxRow = Math.max(...gens.map(g => byGen[g].length));
  const W = Math.max(maxRow * (NW + GAPX), 280);
  const H = gens.length * (NH + GAPY);
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('width', W);
  svg.setAttribute('height', H);
  // 計算每節點座標
  const pos = {};
  gens.forEach((g, gi) => {
    const row = byGen[g];
    const rowW = row.length * (NW + GAPX) - GAPX;
    const x0 = (W - rowW) / 2;
    row.forEach((n, i) => {
      pos[n.key] = { x: x0 + i * (NW + GAPX) + NW / 2, y: gi * (NH + GAPY) + NH / 2 };
    });
  });
  // 畫親子連線
  LINEAGE.edges.forEach(([p, c]) => {
    if (!pos[p] || !pos[c]) return;
    const line = document.createElementNS(SVGNS, 'line');
    line.setAttribute('x1', pos[p].x); line.setAttribute('y1', pos[p].y + NH / 2);
    line.setAttribute('x2', pos[c].x); line.setAttribute('y2', pos[c].y - NH / 2);
    line.setAttribute('stroke', '#C9A96E'); line.setAttribute('stroke-width', '1.5');
    svg.appendChild(line);
  });
  // 畫節點
  LINEAGE.nodes.forEach(n => {
    const p = pos[n.key];
    const g = document.createElementNS(SVGNS, 'g');
    g.style.cursor = 'pointer';
    g.addEventListener('click', () => { closeLineage(); openCard(n.key); });
    const rect = document.createElementNS(SVGNS, 'rect');
    rect.setAttribute('x', p.x - NW / 2); rect.setAttribute('y', p.y - NH / 2);
    rect.setAttribute('width', NW); rect.setAttribute('height', NH);
    rect.setAttribute('rx', 8);
    rect.setAttribute('fill', n.lit ? '#2A5C3A' : '#F0E6D0');
    rect.setAttribute('stroke', n.lit ? '#2A5C3A' : '#C9A96E');
    g.appendChild(rect);
    const txt = document.createElementNS(SVGNS, 'text');
    txt.setAttribute('x', p.x); txt.setAttribute('y', p.y + 4);
    txt.setAttribute('text-anchor', 'middle');
    txt.setAttribute('font-size', '13');
    txt.setAttribute('fill', n.lit ? '#fff' : '#6B5436');
    txt.textContent = n.name.length > 6 ? n.name.slice(0, 6) : n.name;
    g.appendChild(txt);
    svg.appendChild(g);
  });
}
function openLineage() {
  renderLineage();
  document.getElementById('lineagePanel').classList.add('open');
  document.getElementById('lineageOverlay').classList.add('open');
}
function closeLineage() {
  document.getElementById('lineagePanel').classList.remove('open');
  document.getElementById('lineageOverlay').classList.remove('open');
}
