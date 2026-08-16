// 由 app.py 的 /sw.js 路由送出（不是 /static/sw.js），這樣 scope 才會是整個網站。
const CACHE = 'bible-v3';

// 只預先快取同網域、一定拿得到的東西。跨網域的字型與 Leaflet 交給 runtime 快取，
// 因為 addAll() 只要有一個網址失敗就整個 reject，SW 會永遠 activate 不了。
const SHELL = [
  '/',
  '/static/style.css',
  '/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      // 逐個 add 並各自吞掉錯誤：任一項失敗不該讓整個安裝失敗。
      .then(c => Promise.all(SHELL.map(u => c.add(u).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

function put(req, res) {
  // 只存成功且可快取的回應；opaque(status 0) 與錯誤頁不要污染快取。
  if (res && res.ok) {
    const clone = res.clone();
    caches.open(CACHE).then(c => c.put(req, clone)).catch(() => {});
  }
  return res;
}

function cacheFirst(req) {
  return caches.match(req).then(hit => hit || fetch(req).then(res => put(req, res)));
}

function networkFirst(req) {
  return fetch(req)
    .then(res => put(req, res))
    .catch(() => caches.match(req).then(hit => {
      if (hit) return hit;
      // 沒讀過的章節在離線時至少回首頁，不要給瀏覽器的錯誤畫面。
      if (req.mode === 'navigate') return caches.match('/');
      return Response.error();
    }));
}

self.addEventListener('fetch', e => {
  // POST 不能進 Cache Storage（cache.put 會丟 InvalidStateError），
  // /api/explain 就是 POST，直接放行不要攔。
  if (e.request.method !== 'GET') return;

  const url = new URL(e.request.url);

  // 靜態資源與 CDN：cache-first，離線也能開。
  if (url.origin !== self.location.origin || url.pathname.startsWith('/static/')) {
    e.respondWith(cacheFirst(e.request));
    return;
  }

  // 經文頁與 API：network-first，保證線上看到的是最新標註，離線時回快取。
  e.respondWith(networkFirst(e.request));
});
