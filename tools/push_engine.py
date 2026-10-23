"""Push data.js (the content) into Supabase as engine row 'main' (Oct 23 2026).
Run after any data.js change:  python tools/push_engine.py
Needs D:/VideoAgent/burger-content-engine/.env with SUPABASE_SECRET_KEY (never committed)."""
import json, os, urllib.request
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = dict(l.strip().split("=", 1) for l in open(os.path.join(HERE, ".env")) if "=" in l and not l.startswith("#"))
URL = "https://jtfyylkcznycxujdgahq.supabase.co"
s = open(os.path.join(HERE, "data.js"), encoding="utf-8").read()
E = json.loads(s[s.index("{"):].rstrip().rstrip(";"))
key = env["SUPABASE_SECRET_KEY"]
req = urllib.request.Request(URL + "/rest/v1/engine?on_conflict=id", method="POST",
    data=json.dumps([{"id": "main", "data": E}]).encode(),
    headers={"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json",
             "Prefer": "resolution=merge-duplicates,return=minimal"})
urllib.request.urlopen(req)
print("engine pushed:", len(E["cards"]), "cards,", len(E.get("scripts", [])), "scripts")
