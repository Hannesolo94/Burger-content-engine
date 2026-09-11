"""Pull the YouTube numbers the API will actually give us and write metrics.json.

Runs in GitHub Actions off three repository secrets: YT_CLIENT_ID, YT_CLIENT_SECRET,
YT_REFRESH_TOKEN. Nothing is stored in the repo.

What it gets, all verified against Google's YouTube Analytics API reference:
  views, estimatedMinutesWatched, averageViewDuration, averageViewPercentage,
  subscribersGained, subscribersLost, and the traffic source split.

What it cannot get, so the site keeps reading these from the manual Studio reads
already in data.js: thumbnail impressions and impression click through rate.
adImpressions is a monetisation metric and is not the same number.

Run it locally with the same three values in the environment to test.
"""
import json, os, sys, urllib.parse, urllib.request, datetime

CID = os.environ.get("YT_CLIENT_ID")
CSEC = os.environ.get("YT_CLIENT_SECRET")
RTOK = os.environ.get("YT_REFRESH_TOKEN")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "metrics.json")

if not (CID and CSEC and RTOK):
    sys.exit("Set YT_CLIENT_ID, YT_CLIENT_SECRET and YT_REFRESH_TOKEN.")


def post(url, data):
    body = urllib.parse.urlencode(data).encode()
    with urllib.request.urlopen(urllib.request.Request(url, body)) as r:
        return json.load(r)


def get(url, token, params):
    q = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(q, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


token = post("https://oauth2.googleapis.com/token", {
    "client_id": CID, "client_secret": CSEC,
    "refresh_token": RTOK, "grant_type": "refresh_token"})["access_token"]

today = datetime.date.today()
start = today - datetime.timedelta(days=28)
AN = "https://youtubeanalytics.googleapis.com/v2/reports"
DATA = "https://www.googleapis.com/youtube/v3/"

out = {"pulled": today.isoformat(), "window": {"start": start.isoformat(), "end": today.isoformat()}}

# ---- channel totals ----
ch = get(DATA + "channels", token, {"part": "statistics,snippet", "mine": "true"})
out["channels"] = [{
    "id": c["id"], "title": c["snippet"]["title"],
    "subs": int(c["statistics"].get("subscriberCount", 0)),
    "videos": int(c["statistics"].get("videoCount", 0)),
    "views": int(c["statistics"].get("viewCount", 0)),
} for c in ch.get("items", [])]

# ---- how far the API has actually finalised ----
# It runs about three days behind Studio. Without this the page would show numbers
# that are lower than Studio and look like a bug.
day = get(AN, token, {
    "ids": "channel==MINE", "startDate": (today - datetime.timedelta(days=10)).isoformat(),
    "endDate": today.isoformat(), "metrics": "views", "dimensions": "day", "sort": "day"})
out["dataThrough"] = day["rows"][-1][0] if day.get("rows") else None
out["lagDays"] = (today - datetime.date.fromisoformat(out["dataThrough"])).days if out["dataThrough"] else None

# ---- channel totals for the window, straight from the API ----
tot = get(AN, token, {
    "ids": "channel==MINE", "startDate": start.isoformat(), "endDate": today.isoformat(),
    "metrics": "views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost"})
tcols = [h["name"] for h in tot.get("columnHeaders", [])]
out["totals"] = dict(zip(tcols, tot["rows"][0])) if tot.get("rows") else {}

# ---- per video, last 28 days ----
rep = get(AN, token, {
    "ids": "channel==MINE", "startDate": start.isoformat(), "endDate": today.isoformat(),
    "metrics": "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
               "subscribersGained,subscribersLost",
    "dimensions": "video", "sort": "-views", "maxResults": 50})
cols = [h["name"] for h in rep.get("columnHeaders", [])]
rows = [dict(zip(cols, r)) for r in rep.get("rows", [])]

# titles for those ids
ids = [r["video"] for r in rows][:50]
titles = {}
if ids:
    v = get(DATA + "videos", token, {"part": "snippet,contentDetails", "id": ",".join(ids)})
    for it in v.get("items", []):
        titles[it["id"]] = {"title": it["snippet"]["title"],
                            "published": it["snippet"]["publishedAt"][:10],
                            "runtime": it["contentDetails"]["duration"]}
for r in rows:
    r.update(titles.get(r["video"], {}))
out["videos"] = rows

# ---- where the views came from ----
src = get(AN, token, {
    "ids": "channel==MINE", "startDate": start.isoformat(), "endDate": today.isoformat(),
    "metrics": "views,estimatedMinutesWatched",
    "dimensions": "insightTrafficSourceType", "sort": "-views"})
scols = [h["name"] for h in src.get("columnHeaders", [])]
out["traffic"] = [dict(zip(scols, r)) for r in src.get("rows", [])]

out["missing"] = {
    "impressions": "Not exposed by the YouTube Analytics API. Read it in Studio.",
    "impressionClickThroughRate": "Not exposed by the YouTube Analytics API. Read it in Studio.",
}

json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1)
print("wrote", OUT, "|", len(out["videos"]), "videos |", len(out["channels"]), "channels")
