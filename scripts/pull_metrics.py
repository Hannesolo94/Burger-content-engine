"""Pull the YouTube numbers the API will give us, for every channel that has a token.

Each channel is its own OAuth grant, because each channel is a separate grant on the
consent screen. Set these repository secrets:

    HanneBurger   YT_CLIENT_ID        YT_CLIENT_SECRET        YT_REFRESH_TOKEN
    Burgercam     YT_BC_CLIENT_ID     YT_BC_CLIENT_SECRET     YT_BC_REFRESH_TOKEN

A channel with no token is skipped, so this runs fine with only one of them set.

What it gets, all verified against Google's YouTube Analytics API reference:
  views, estimatedMinutesWatched, averageViewDuration, averageViewPercentage,
  subscribersGained, subscribersLost, and the traffic source split.

What it cannot get, so the site keeps reading these from the manual Studio reads
already in data.js: thumbnail impressions and impression click through rate.
adImpressions is a monetisation metric and is not the same number.

Run it locally with the same values in the environment to test.
"""
import json, os, sys, urllib.parse, urllib.request, urllib.error, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "metrics.json")
AN = "https://youtubeanalytics.googleapis.com/v2/reports"
DATA = "https://www.googleapis.com/youtube/v3/"

CHANNELS = [
    {"key": "hanneburger", "prefix": "YT_"},
    {"key": "burgercam", "prefix": "YT_BC_"},
]


def post(url, data):
    body = urllib.parse.urlencode(data).encode()
    with urllib.request.urlopen(urllib.request.Request(url, body)) as r:
        return json.load(r)


def get(url, token, params):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params),
                                 headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def table(payload):
    cols = [h["name"] for h in payload.get("columnHeaders", [])]
    return [dict(zip(cols, r)) for r in payload.get("rows", [])]


def pull(key, prefix, today):
    cid = os.environ.get(prefix + "CLIENT_ID")
    csec = os.environ.get(prefix + "CLIENT_SECRET")
    rtok = os.environ.get(prefix + "REFRESH_TOKEN")
    if not (cid and csec and rtok):
        print("skip %s, no %sREFRESH_TOKEN" % (key, prefix))
        return None

    try:
        token = post("https://oauth2.googleapis.com/token", {
            "client_id": cid, "client_secret": csec,
            "refresh_token": rtok, "grant_type": "refresh_token"})["access_token"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if "invalid_grant" in body:
            print("\n" + "=" * 70)
            print("%s: the refresh token no longer works." % key)
            print("Almost always this one cause: the OAuth consent screen is still in")
            print("Testing status, and Google revokes every token seven days after consent.")
            print("Fix it once, not weekly: Google Cloud console, Google Auth Platform,")
            print("Audience, Publish app. Then run the consent script again for this channel.")
            print("Raw response: " + body[:200])
            print("=" * 70 + "\n")
        else:
            print("%s: token exchange failed, HTTP %s %s" % (key, e.code, body[:200]))
        return None

    start = today - datetime.timedelta(days=28)
    win = {"ids": "channel==MINE", "startDate": start.isoformat(), "endDate": today.isoformat()}

    ch = get(DATA + "channels", token, {"part": "statistics,snippet", "mine": "true"})
    items = ch.get("items", [])
    if not items:
        print("skip %s, that token reads no channel" % key)
        return None
    c = items[0]
    info = {"key": key, "id": c["id"], "title": c["snippet"]["title"],
            "subs": int(c["statistics"].get("subscriberCount", 0)),
            "videos": int(c["statistics"].get("videoCount", 0)),
            "views": int(c["statistics"].get("viewCount", 0))}

    # How far the API has actually finalised. It runs about three days behind Studio,
    # and without this the page would show numbers below Studio and look broken.
    day = get(AN, token, dict(win, startDate=(today - datetime.timedelta(days=10)).isoformat(),
                              metrics="views", dimensions="day", sort="day"))
    rows = day.get("rows", [])
    through = rows[-1][0] if rows else None

    totals = table(get(AN, token, dict(
        win, metrics="views,estimatedMinutesWatched,averageViewDuration,"
                     "subscribersGained,subscribersLost")))
    totals = totals[0] if totals else {}

    vids = table(get(AN, token, dict(
        win, metrics="views,estimatedMinutesWatched,averageViewDuration,"
                     "averageViewPercentage,subscribersGained,subscribersLost",
        dimensions="video", sort="-views", maxResults=50)))

    ids = [v["video"] for v in vids][:50]
    if ids:
        meta = get(DATA + "videos", token, {"part": "snippet,contentDetails", "id": ",".join(ids)})
        by = {it["id"]: it for it in meta.get("items", [])}
        for v in vids:
            it = by.get(v["video"])
            if it:
                v["title"] = it["snippet"]["title"]
                v["published"] = it["snippet"]["publishedAt"][:10]
                v["runtime"] = it["contentDetails"]["duration"]
    for v in vids:
        v["channel"] = key

    traffic = table(get(AN, token, dict(
        win, metrics="views,estimatedMinutesWatched",
        dimensions="insightTrafficSourceType", sort="-views")))

    print("%s: %s, %d videos, complete to %s" % (key, info["title"], len(vids), through))
    return {"info": info, "totals": totals, "videos": vids, "traffic": traffic,
            "dataThrough": through,
            "lagDays": (today - datetime.date.fromisoformat(through)).days if through else None,
            "window": {"start": start.isoformat(), "end": today.isoformat()}}


def main():
    today = datetime.date.today()
    out = {"pulled": today.isoformat(), "channels": [], "videos": [], "byChannel": {}}
    ok = 0
    for spec in CHANNELS:
        try:
            got = pull(spec["key"], spec["prefix"], today)
        except urllib.error.HTTPError as e:
            print("%s failed: HTTP %s %s" % (spec["key"], e.code, e.read()[:200]))
            continue
        if not got:
            continue
        ok += 1
        out["channels"].append(got["info"])
        out["videos"].extend(got["videos"])
        out["byChannel"][got["info"]["id"]] = {
            "key": got["info"]["key"], "totals": got["totals"], "traffic": got["traffic"],
            "dataThrough": got["dataThrough"], "lagDays": got["lagDays"], "window": got["window"]}

    if not ok:
        sys.exit("No channel had a usable token. Nothing written.")

    # The page shows one lag line, so report the furthest behind of the channels pulled.
    through = [b["dataThrough"] for b in out["byChannel"].values() if b["dataThrough"]]
    out["dataThrough"] = min(through) if through else None
    lags = [b["lagDays"] for b in out["byChannel"].values() if b["lagDays"] is not None]
    out["lagDays"] = max(lags) if lags else None
    out["window"] = list(out["byChannel"].values())[0]["window"]
    out["missing"] = {
        "impressions": "Not exposed by the YouTube Analytics API. Read it in Studio.",
        "impressionClickThroughRate": "Not exposed by the YouTube Analytics API. Read it in Studio.",
    }

    json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1)
    print("wrote %s | %d channels | %d videos | complete to %s"
          % (OUT, len(out["channels"]), len(out["videos"]), out["dataThrough"]))


if __name__ == "__main__":
    main()
