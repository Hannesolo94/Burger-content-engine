/* Burger Content Engine sync (Oct 23 2026).
   Loads the content and every saved state blob from Supabase, so the board, scripts and edits are the same
   on the phone and the PC. Works offline from the last copy. Falls back to data.js when this device is not paired.
   Pair a device once by opening the private link (?k=...). The key never lives in this repo. */
(function(){
  var URL_ = "https://jtfyylkcznycxujdgahq.supabase.co";
  var PUB = "PUBLISHABLE_KEY_HERE";          /* the publishable key is safe in page source: RLS has zero policies */
  var K_KEY = "burger-engine-key", K_CACHE = "burger-engine-cache", K_Q = "burger-engine-queue", K_THEME = "burger-engine-theme";
  var LOCAL_ONLY = [K_KEY, K_CACHE, K_Q, K_THEME];
  var rawSet = Storage.prototype.setItem;
  function get(k){ try { return localStorage.getItem(k); } catch(e){ return null; } }
  function set(k, v){ try { rawSet.call(localStorage, k, v); } catch(e){} }

  /* pairing: ?k=<token> once, then it is removed from the address bar */
  try {
    var u = new URL(location.href), k = u.searchParams.get("k");
    if (k){ set(K_KEY, k); u.searchParams.delete("k"); history.replaceState(null, "", u.pathname + (u.search || "") + u.hash); }
  } catch(e){}
  var token = get(K_KEY), live = !!(token && PUB.indexOf("_HERE") < 0);

  function rpc(fn, body, ms){
    var ctl = window.AbortController ? new AbortController() : null;
    var timer = ctl ? setTimeout(function(){ ctl.abort(); }, ms || 8000) : null;
    return fetch(URL_ + "/rest/v1/rpc/" + fn, { method: "POST", signal: ctl && ctl.signal,
      headers: { "apikey": PUB, "Authorization": "Bearer " + PUB, "Content-Type": "application/json" },
      body: JSON.stringify(body) }).then(function(r){ if (timer) clearTimeout(timer);
        if (!r.ok) throw new Error("http " + r.status); return r.json(); });
  }

  var badge = function(txt, ok){
    var el = document.getElementById("stamp"); if (!el) return;
    var s = document.getElementById("sync-dot");
    if (!s){ s = document.createElement("span"); s.id = "sync-dot"; s.className = "mini"; s.style.marginLeft = "8px"; el.parentNode.insertBefore(s, el.nextSibling); }
    s.textContent = "· " + txt; s.style.color = ok ? "var(--lime)" : "var(--yellow)";
  };

  /* every local save of a burger-engine-* blob also goes to Supabase (queued, so offline edits catch up) */
  var queue = {}; try { queue = JSON.parse(get(K_Q) || "{}"); } catch(e){ queue = {}; }
  var flushing = false, timerF = null;
  function flush(){
    if (!live || flushing) return;
    var keys = Object.keys(queue); if (!keys.length){ badge("synced", true); return; }
    flushing = true; var key = keys[0], val = queue[key];
    rpc("be_put", { p_token: token, p_key: key, p_value: val }).then(function(){
      if (queue[key] === val) delete queue[key]; set(K_Q, JSON.stringify(queue)); flushing = false; flush();
    }).catch(function(){ flushing = false; badge("offline, saved on this device", false); });
  }
  Storage.prototype.setItem = function(k, v){
    rawSet.call(this, k, v);
    if (this === window.localStorage && live && /^burger-engine-/.test(k) && LOCAL_ONLY.indexOf(k) < 0){
      var parsed; try { parsed = JSON.parse(v); } catch(e){ parsed = v; }
      queue[k] = parsed; set(K_Q, JSON.stringify(queue));
      clearTimeout(timerF); timerF = setTimeout(flush, 600);
    }
  };
  window.addEventListener("online", flush);

  /* installable app: service worker caches the shell for offline */
  if ("serviceWorker" in navigator) window.addEventListener("load", function(){ navigator.serviceWorker.register("sw.js").catch(function(){}); });

  function boot(){ if (window.__boot) window.__boot(); }
  if (!live){ document.addEventListener("DOMContentLoaded", function(){ boot(); badge(token ? "not connected yet" : "local only", false); }); return; }

  /* offline first: last good copy straight away if the network is slow, then the live data */
  function apply(d){
    if (d.engine) { window.ENGINE = d.engine; set(K_CACHE, JSON.stringify(d.engine)); }
    var st = d.state || {};
    Object.keys(st).forEach(function(key){ if (!(key in queue)) set(key, JSON.stringify(st[key].v)); });
  }
  var started = false;
  function start(){ if (started) return; started = true; boot(); }
  document.addEventListener("DOMContentLoaded", function(){
    rpc("be_get", { p_token: token }, 6000).then(function(d){
      apply(d); start(); badge("synced", true); flush();
    }).catch(function(){
      try { var c = JSON.parse(get(K_CACHE) || "null"); if (c) window.ENGINE = c; } catch(e){}
      start(); badge("offline, last copy", false);
    });
  });

})();
