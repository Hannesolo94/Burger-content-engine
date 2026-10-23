"""Push data.js (the content) into Supabase as engine row 'main' (Oct 23 2026).
Run after any data.js change:  python tools/push_engine.py
Goes through the token-gated be_put_engine RPC with the publishable key, so no secret key is needed.
Reads BURGER_ENGINE_TOKEN and SUPABASE_PUBLISHABLE_KEY from .env (never committed)."""
import json, os, urllib.request
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = dict(l.strip().split("=", 1) for l in open(os.path.join(HERE, ".env")) if "=" in l and not l.startswith("#"))
URL = "https://jtfyylkcznycxujdgahq.supabase.co"
s = open(os.path.join(HERE, "data.js"), encoding="utf-8").read()
E = json.loads(s[s.index("{"):].rstrip().rstrip(";"))
key = env["SUPABASE_PUBLISHABLE_KEY"]
req = urllib.request.Request(URL + "/rest/v1/rpc/be_put_engine", method="POST",
    data=json.dumps({"p_token": env["BURGER_ENGINE_TOKEN"], "p_data": E}).encode(),
    headers={"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json"})
urllib.request.urlopen(req)
print("engine pushed:", len(E["cards"]), "cards,", len(E.get("scripts", [])), "scripts")
