// Service worker: lets the portal install as an app and open its screens quickly.
// It never stores anything from /api, so complaints, logins and codes are always live.
const VERSION = "kgt-v2";
const SHELL = ["/assets/portal.css", "/assets/portal.js", "/assets/i18n.js", "/assets/icons.svg", "/assets/pwa.js", "/offline"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => cache.addAll(SHELL).catch(() => {})).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/qr.") || url.pathname === "/sw.js") return;   // always live
  if (url.pathname.startsWith("/assets/")) {
    // Styles, scripts and icons: show the saved copy at once and refresh it in the background.
    event.respondWith(caches.open(VERSION).then(async (cache) => {
      const saved = await cache.match(request);
      const fresh = fetch(request).then((response) => { if (response.ok) cache.put(request, response.clone()); return response; }).catch(() => saved);
      return saved || fresh;
    }));
    return;
  }
  if (request.mode === "navigate") {
    // Pages are always fetched fresh. Only when there is no network do we show the offline note.
    event.respondWith(fetch(request).catch(() => caches.match("/offline").then((page) => page || new Response("You are offline.", { status: 503 }))));
  }
});
