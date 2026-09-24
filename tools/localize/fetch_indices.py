"""Bake the Bangumi indexes used by the built-in presets into the repo.

Output: client/public/gamedata/indices.json
  { "75522": { "title": "拉邦歌马杂", "sids": [123, 456, ...] }, ... }

Only subject ids are stored; the client intersects them with the local subject
pool, so an index may list works we do not have.
"""
import json
import os
import sys
import time

import requests

REPO = os.environ["ACG_REPO"]
OUT = os.path.join(REPO, "client", "public", "gamedata")
API = "https://api.bgm.tv"
PROXY = os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:7890"
IDS = ["75522", "77344", "77186", "76637"]

S = requests.Session()
S.proxies = {"http": PROXY, "https": PROXY}
S.headers.update({"User-Agent": "acg-guessr-local-build/1.0"})


def get(url, params=None):
    for a in range(4):
        try:
            r = S.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            print("  HTTP %s %s" % (r.status_code, url), flush=True)
        except Exception as e:
            print("  retry %d: %s" % (a + 1, e), flush=True)
        time.sleep(1.5 ** a)
    raise RuntimeError("failed: %s" % url)


def main():
    with open(os.path.join(OUT, "subjects.json"), "r", encoding="utf-8") as fh:
        local_subjects = set(json.load(fh).keys())

    out = {}
    for iid in IDS:
        info = get("%s/v0/indices/%s" % (API, iid))
        title = (info or {}).get("title") or ""
        sids = []
        offset = 0
        while True:
            page = get("%s/v0/indices/%s/subjects" % (API, iid),
                       {"limit": 100, "offset": offset})
            data = (page or {}).get("data") or []
            if not data:
                break
            sids.extend(int(x["id"]) for x in data)
            offset += len(data)
            total = (page or {}).get("total") or 0
            if offset >= total:
                break
        # de-dup, keep order
        seen = set()
        sids = [s for s in sids if not (s in seen or seen.add(s))]
        hit = [s for s in sids if str(s) in local_subjects]
        out[iid] = {"title": title, "sids": sids}
        print("  index %s %-12s listed=%-4d local-playable=%d" % (iid, title, len(sids), len(hit)),
              flush=True)

    p = os.path.join(OUT, "indices.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print("wrote %s (%d bytes)" % (p, os.path.getsize(p)), flush=True)


if __name__ == "__main__":
    sys.exit(main())
