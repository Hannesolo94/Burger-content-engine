/* Burger Content Engine service worker (Oct 23 2026): keeps the app shell for offline.
   Pages and scripts: network first, cache as fallback. Supabase calls are never cached (sync.js keeps its own copy). */
var C = "burger-engine-v1";
var SHELL = ["./", "index.html", "data.js", "sync.js", "manifest.webmanifest", "icon-512.png", "apple-touch-icon.png", "favicon.ico"];
self.addEventListener("install", function(e){ e.waitUntil(caches.open(C).then(function(c){ return c.addAll(SHELL); })); self.skipWaiting(); });
self.addEventListener("activate", function(e){
  e.waitUntil(caches.keys().then(function(ks){ return Promise.all(ks.filter(function(k){ return k !== C; }).map(function(k){ return caches.delete(k); })); }));
  self.clients.claim();
});
self.addEventListener("fetch", function(e){
  var u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.hostname.indexOf("supabase.co") >= 0) return;
  e.respondWith(fetch(e.request).then(function(r){
    if (r.ok && (u.origin === location.origin || u.hostname.indexOf("fonts.") >= 0)){ var copy = r.clone(); caches.open(C).then(function(c){ c.put(e.request, copy); }); }
    return r;
  }).catch(function(){ return caches.match(e.request, { ignoreSearch: true }).then(function(m){ return m || caches.match("index.html"); }); }));
});
