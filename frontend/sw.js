// Service worker: makes the app start even without a connection.
// The app shell (HTML, CSS, JS, icons) comes from a cache; API calls always
// go to the network, because listings and swipes must be fresh.

const CACHE = "wohinder-v1";   // bump the number whenever the shell files change
const SHELL = [
  "./",
  "index.html",
  "style.css",
  "app.js",
  "manifest.webmanifest",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/apple-touch-icon.png",
];

// install: download the shell into the cache
self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

// activate: delete caches from older versions
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

// fetch: shell files network-first (so updates show up while developing),
// falling back to the cache when offline. Everything else is left alone.
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  const isShell = event.request.method === "GET"
    && url.origin === self.location.origin
    && url.pathname.startsWith("/app/");
  if (!isShell) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
