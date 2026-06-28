/* ════════════════════════════════════════════════════════════
   聚焦式教學導覽（Spotlight Tour）— 聖經互動全書版
   - 把背景變暗，用挖空高亮某個元素，旁邊跳出說明氣泡
   - 自包含、無外部依賴
   用法：
     SpotlightTour.auto('read-v1', steps);          // 首次自動跑（localStorage 記住）
     SpotlightTour.start(steps);                     // 立即重看（不檢查記錄）
     SpotlightTour.auto('k', steps, { idleMs: 30000 });
   steps: [{ sel:'CSS選擇器', title:'標題', text:'說明', spot:留白px, open:'展開控制項選擇器' }, ...]
   找不到/隱藏的步驟自動略過；sel 留空 → 置中歡迎/結語卡。
   ════════════════════════════════════════════════════════════ */
(function () {
  if (window.SpotlightTour) return;

  // 主色：沿用 app 墨綠（#2A5C3A）與較深的 #21492e
  var STYLE_ID = 'spotlight-tour-style';
  var CSS = '' +
    '#st-overlay{position:fixed;inset:0;z-index:10000;display:none;}' +
    '#st-hole{position:fixed;border-radius:12px;box-shadow:0 0 0 9999px rgba(42,26,8,.66);' +
      'transition:all .32s cubic-bezier(.22,1,.36,1);pointer-events:none;border:2px solid rgba(42,92,58,.95);}' +
    '#st-tip{position:fixed;z-index:10001;max-width:320px;width:calc(100vw - 32px);' +
      'background:#FBF6EA;border-radius:16px;box-shadow:0 18px 50px rgba(0,0,0,.35);' +
      'padding:18px 18px 14px;box-sizing:border-box;' +
      'font-family:"Noto Serif TC","Songti TC","PingFang TC","Microsoft JhengHei",serif;' +
      'transition:top .3s cubic-bezier(.22,1,.36,1),left .3s cubic-bezier(.22,1,.36,1);' +
      'opacity:0;animation:stFade .3s ease forwards;}' +
    '@keyframes stFade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}' +
    '#st-tip .st-step{font-size:.72rem;font-weight:700;color:#2A5C3A;letter-spacing:.05em;margin-bottom:6px;}' +
    '#st-tip .st-title{font-size:1.05rem;font-weight:800;color:#2A1A08;line-height:1.4;margin-bottom:6px;}' +
    '#st-tip .st-text{font-size:.88rem;color:#5A4628;line-height:1.7;}' +
    '#st-tip .st-dots{display:flex;gap:5px;margin-top:14px;flex-wrap:wrap;}' +
    '#st-tip .st-dot{width:7px;height:7px;border-radius:50%;background:#E0D2B4;transition:background .2s,width .2s;}' +
    '#st-tip .st-dot.on{background:#2A5C3A;width:18px;border-radius:4px;}' +
    '#st-tip .st-btns{display:flex;align-items:center;gap:8px;margin-top:14px;}' +
    '#st-tip .st-skip{background:none;border:none;color:#A89878;font-size:.82rem;cursor:pointer;padding:8px 2px;margin-right:auto;font-family:inherit;}' +
    '#st-tip .st-skip:hover{color:#8B6840;}' +
    '#st-tip .st-btn{border:none;border-radius:9px;padding:9px 16px;font-size:.85rem;font-weight:700;' +
      'cursor:pointer;font-family:inherit;transition:background .15s,transform .1s;}' +
    '#st-tip .st-btn:active{transform:scale(.96);}' +
    '#st-tip .st-prev{background:#EFE6D2;color:#6B5436;}' +
    '#st-tip .st-prev:hover{background:#e5d8be;}' +
    '#st-tip .st-next{background:#2A5C3A;color:#fff;}' +
    '#st-tip .st-next:hover{background:#21492e;}' +
    '#st-tip .st-arrow{position:absolute;width:14px;height:14px;background:#FBF6EA;transform:rotate(45deg);}' +
    '#st-banner{position:fixed;top:0;left:0;right:0;z-index:10002;' +
      'background:linear-gradient(90deg,#21492e,#2A5C3A);color:#fff;' +
      'display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap;' +
      'padding:11px 16px;font-size:.92rem;font-weight:700;text-align:center;' +
      'box-shadow:0 4px 16px rgba(42,92,58,.45);' +
      'font-family:"Noto Serif TC","PingFang TC","Microsoft JhengHei",serif;' +
      'animation:stBannerIn .35s cubic-bezier(.22,1,.36,1) both;}' +
    '@keyframes stBannerIn{from{transform:translateY(-100%)}to{transform:none}}' +
    '#st-banner .st-banner-dot{width:9px;height:9px;border-radius:50%;background:#fff;' +
      'animation:stBlink 1.1s ease-in-out infinite;}' +
    '@keyframes stBlink{0%,100%{opacity:.35}50%{opacity:1}}' +
    '#st-banner .st-banner-sub{font-weight:500;font-size:.82rem;opacity:.92;}' +
    '#st-banner .st-banner-exit{background:rgba(255,255,255,.25);border:none;color:#fff;' +
      'border-radius:100px;padding:5px 14px;font-size:.82rem;font-weight:700;cursor:pointer;font-family:inherit;}' +
    '#st-banner .st-banner-exit:hover{background:rgba(255,255,255,.4);}' +
    '@media (prefers-reduced-motion: reduce){#st-hole{transition:none}#st-tip{transition:none;animation:none}}';

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var s = document.createElement('style');
    s.id = STYLE_ID;
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  var state = { steps: [], i: 0, key: null, overlay: null, hole: null, tip: null, banner: null,
                idleMs: 22000, idleTimer: null, onActivity: null, reverts: [] };

  function clearIdle() { if (state.idleTimer) { clearTimeout(state.idleTimer); state.idleTimer = null; } }
  function resetIdle() { clearIdle(); if (state.idleMs > 0) state.idleTimer = setTimeout(finish, state.idleMs); }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function isVisible(el) { return !!(el && el.getClientRects().length); }

  function activateOpener(openSel) {
    var o = document.querySelector(openSel);
    if (!o) return;
    if (o.tagName === 'INPUT' && o.type === 'checkbox') {
      if (!o.checked) { o.checked = true; o.dispatchEvent(new Event('change', { bubbles: true })); state.reverts.push(o); }
    } else { try { o.click(); } catch (e) {} }
  }
  function maybeReveal(step) {
    if (!step.open) return;
    var t = document.querySelector(step.sel);
    if (t && isVisible(t)) return;
    var opens = Array.isArray(step.open) ? step.open : [step.open];
    opens.forEach(activateOpener);
  }

  function buildDom() {
    var overlay = document.createElement('div'); overlay.id = 'st-overlay';
    var hole = document.createElement('div'); hole.id = 'st-hole';
    var tip = document.createElement('div'); tip.id = 'st-tip';
    overlay.appendChild(hole);
    document.body.appendChild(overlay);
    document.body.appendChild(tip);
    var banner = document.createElement('div'); banner.id = 'st-banner';
    banner.innerHTML =
      '<span class="st-banner-dot"></span><span>教學導覽進行中</span>' +
      '<span class="st-banner-sub">畫面暫停捲動，請點下方「下一步」</span>' +
      '<button class="st-banner-exit" type="button">結束導覽</button>';
    banner.querySelector('.st-banner-exit').onclick = finish;
    document.body.appendChild(banner);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) next(); });
    state.overlay = overlay; state.hole = hole; state.tip = tip; state.banner = banner;
  }

  function render() {
    var step = state.steps[state.i];
    resetIdle();
    // step.before：進入此步前先執行（例如打開某個面板／卡片再導覽其內部）
    if (typeof step.before === 'function') {
      try { step.before(); } catch (e) {}
      setTimeout(function () { if (state.steps[state.i] === step) renderBody(step); }, step.beforeWait || 300);
    } else {
      renderBody(step);
    }
  }
  function renderBody(step) {
    if (!step.sel) { requestAnimationFrame(function () { positionCenter(step); }); return; }
    maybeReveal(step);
    var el = document.querySelector(step.sel);
    if (!el || !isVisible(el)) { next(); return; }
    try { el.scrollIntoView({ block: 'center', inline: 'nearest' }); } catch (e) { el.scrollIntoView(); }
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        position(el, step);
        setTimeout(function () { if (state.steps[state.i] === step) position(el, step); }, 260);
      });
    });
  }

  function position(el, step) {
    var pad = step.spot != null ? step.spot : 8;
    var r = el.getBoundingClientRect();
    var hole = state.hole, tip = state.tip;
    var hx = r.left - pad, hy = r.top - pad, hw = r.width + pad * 2, hh = r.height + pad * 2;
    hole.style.left = hx + 'px'; hole.style.top = hy + 'px';
    hole.style.width = hw + 'px'; hole.style.height = hh + 'px';
    fillTip(step);
    var vw = window.innerWidth, vh = window.innerHeight;
    var tw = tip.offsetWidth, th = tip.offsetHeight, gap = 14;
    var below = hy + hh + gap, topMin = 58, top, arrowTop;
    if (below + th <= vh - 8) { top = below; arrowTop = true; }
    else if (hy - gap - th >= topMin) { top = hy - gap - th; arrowTop = false; }
    else { top = clamp(vh - th - 16, topMin, vh - th - 8); arrowTop = false; }
    var centerX = hx + hw / 2;
    var left = clamp(centerX - tw / 2, 12, vw - tw - 12);
    tip.style.top = top + 'px'; tip.style.left = left + 'px';
    var arrow = tip.querySelector('.st-arrow');
    var ax = clamp(centerX - left - 7, 14, tw - 28);
    arrow.style.left = ax + 'px';
    if (arrowTop) { arrow.style.top = '-7px'; arrow.style.boxShadow = '-2px -2px 4px rgba(0,0,0,.04)'; }
    else { arrow.style.top = (th - 7) + 'px'; arrow.style.boxShadow = '2px 2px 4px rgba(0,0,0,.04)'; }
  }

  function fillTip(step) {
    var tip = state.tip, total = state.steps.length, dots = '';
    for (var d = 0; d < total; d++) dots += '<span class="st-dot' + (d === state.i ? ' on' : '') + '"></span>';
    var isLast = state.i === total - 1, isFirst = state.i === 0;
    tip.innerHTML =
      '<div class="st-arrow"></div>' +
      '<div class="st-step">' + (state.i + 1) + ' / ' + total + '</div>' +
      '<div class="st-title">' + esc(step.title) + '</div>' +
      '<div class="st-text">' + esc(step.text) + '</div>' +
      '<div class="st-dots">' + dots + '</div>' +
      '<div class="st-btns">' +
        '<button class="st-skip" type="button">略過</button>' +
        (isFirst ? '' : '<button class="st-btn st-prev" type="button">上一步</button>') +
        '<button class="st-btn st-next" type="button">' + (isLast ? '完成 ✓' : '下一步') + '</button>' +
      '</div>';
    tip.querySelector('.st-skip').onclick = finish;
    tip.querySelector('.st-next').onclick = next;
    var prev = tip.querySelector('.st-prev');
    if (prev) prev.onclick = back;
    tip.style.animation = 'none'; tip.offsetHeight; tip.style.animation = '';
  }

  function positionCenter(step) {
    var hole = state.hole, tip = state.tip, vw = window.innerWidth, vh = window.innerHeight;
    hole.style.left = (vw / 2) + 'px'; hole.style.top = (vh / 2) + 'px';
    hole.style.width = '0px'; hole.style.height = '0px';
    fillTip(step);
    var tw = tip.offsetWidth, th = tip.offsetHeight;
    tip.style.left = clamp((vw - tw) / 2, 12, vw - tw - 12) + 'px';
    tip.style.top = clamp((vh - th) / 2, 64, vh - th - 12) + 'px';
    var arrow = tip.querySelector('.st-arrow');
    if (arrow) arrow.style.display = 'none';
  }

  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  function show() {
    injectStyle();
    if (!state.overlay) buildDom();
    state.overlay.style.display = 'block';
    state.tip.style.display = 'block';
    if (state.banner) state.banner.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    state.onKey = function (e) {
      if (e.key === 'Escape') finish();
      else if (e.key === 'ArrowRight' || e.key === 'Enter') next();
      else if (e.key === 'ArrowLeft') back();
    };
    document.addEventListener('keydown', state.onKey);
    state.onResize = function () {
      var step = state.steps[state.i]; if (!step) return;
      if (!step.sel) { positionCenter(step); return; }
      var el = document.querySelector(step.sel); if (el) position(el, step);
    };
    window.addEventListener('resize', state.onResize);
    state.onActivity = function () { resetIdle(); };
    ['pointerdown', 'keydown', 'wheel', 'touchmove'].forEach(function (ev) {
      document.addEventListener(ev, state.onActivity, { passive: true });
    });
    render();
  }

  function next() { if (state.i >= state.steps.length - 1) { finish(); } else { state.i++; render(); } }
  function back() { if (state.i > 0) { state.i--; render(); } }

  function finish() {
    clearIdle();
    if (state.reverts && state.reverts.length) {
      state.reverts.forEach(function (o) {
        try { o.checked = false; o.dispatchEvent(new Event('change', { bubbles: true })); } catch (e) {}
      });
      state.reverts = [];
    }
    if (state.overlay) state.overlay.style.display = 'none';
    if (state.tip) state.tip.style.display = 'none';
    if (state.banner) state.banner.style.display = 'none';
    document.body.style.overflow = '';
    if (state.onKey) document.removeEventListener('keydown', state.onKey);
    if (state.onResize) window.removeEventListener('resize', state.onResize);
    if (state.onActivity) {
      ['pointerdown', 'keydown', 'wheel', 'touchmove'].forEach(function (ev) {
        document.removeEventListener(ev, state.onActivity);
      });
      state.onActivity = null;
    }
    if (state.key) { try { localStorage.setItem('st_done_' + state.key, '1'); } catch (e) {} }
    if (typeof state.onFinish === 'function') { try { state.onFinish(); } catch (e) {} }
  }

  function start(steps, key, opts) {
    var avail = steps.filter(function (s) {
      if (!s.sel) return true;
      if (s.open && document.querySelector(s.sel)) return true;
      return isVisible(document.querySelector(s.sel));
    });
    if (!avail.some(function (s) { return s.sel; })) return false;
    state.steps = avail; state.i = 0; state.key = key || null; state.reverts = [];
    state.idleMs = (opts && opts.idleMs != null) ? opts.idleMs : 22000;
    state.onFinish = (opts && opts.onFinish) || null;
    show();
    return true;
  }

  window.SpotlightTour = {
    start: function (steps, opts) { return start(steps, null, opts); },
    auto: function (key, steps, opts) {
      try { if (localStorage.getItem('st_done_' + key)) return false; } catch (e) {}
      setTimeout(function () { start(steps, key, opts); }, 900);
      return true;
    },
    reset: function (key) { try { localStorage.removeItem('st_done_' + key); } catch (e) {} }
  };
})();
