// 홈 화면에 추가한 뒤에는 인터넷 없이도 게임이 실행되도록 껍데기를 캐시해 둔다.
const CACHE = 'boglbogl-v1';
const ASSETS = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png'];

self.addEventListener('install', function (e) {
    e.waitUntil(
        caches.open(CACHE)
            .then(function (c) { return c.addAll(ASSETS); })
            .then(function () { return self.skipWaiting(); })
    );
});

self.addEventListener('activate', function (e) {
    e.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(keys.map(function (k) {
                return k === CACHE ? null : caches.delete(k);
            }));
        }).then(function () { return self.clients.claim(); })
    );
});

// 온라인이면 항상 최신본을 받고, 끊겼을 때만 캐시로 실행한다
self.addEventListener('fetch', function (e) {
    if (e.request.method !== 'GET') return;
    e.respondWith(
        fetch(e.request).then(function (res) {
            const copy = res.clone();
            caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
            return res;
        }).catch(function () {
            return caches.match(e.request).then(function (m) {
                return m || caches.match('./index.html');
            });
        })
    );
});
