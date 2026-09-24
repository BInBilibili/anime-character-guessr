"""Download subject covers (Bangumi grid variant) for the subjects we already ship.

Input : $ACG_WORK/covers_urls.json   {sid: {grid, small, common, ...}}
Output: <repo>/client/public/covers/<shard>/<basename>.webp
        $ACG_WORK/covers_data.jsonl  {sid, url, webp, bytes, w, h}

shard = basename[-5:-3].lower()  -- same rule as the character images, and the
same rule toLocalCharPath()/localSubjectImage() use, so shard case can never
disagree between Windows (case-insensitive) and GitHub Pages (case-sensitive).

Resumable: files already on disk are skipped.
Usage:
  python fetch_covers.py --workers 8              # full run
  python fetch_covers.py --workers 6 --limit 60   # calibration sample
"""
import argparse, io, json, os, random, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

import requests
from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ACG_REPO") or os.path.abspath(os.path.join(_HERE, "..", ".."))
WORK = os.environ.get("ACG_WORK") or os.path.join(_HERE, "_work")
os.makedirs(WORK, exist_ok=True)
TMP = WORK
OUT_DIR = os.path.join(REPO, "client", "public", "covers")
URLS = os.path.join(TMP, "covers_urls.json")
LOG = os.path.join(TMP, "covers_data.jsonl")

MAX_EDGE = 120      # grid is ~100px wide; display box is 40 CSS px (80 device px @2x)
QUALITY = 80

lock = threading.Lock()
stats = {"ok": 0, "err": 0, "skip": 0, "bytes": 0}
errors = []


def shard_of(base):
    return base[-5:-3].lower()


def base_of(url):
    return url.rsplit("/", 1)[-1].rsplit(".", 1)[0]


def pick_url(imgs):
    for k in ("grid", "small", "common", "medium", "large"):
        u = imgs.get(k)
        if u:
            return u
    return None


def fetch_one(sid, imgs, sess):
    url = pick_url(imgs)
    if not url:
        with lock:
            stats["err"] += 1
            errors.append((sid, "no-url"))
        return
    base = base_of(url)
    shard = shard_of(base)
    out = os.path.join(OUT_DIR, shard, base + ".webp")
    if os.path.exists(out):
        with lock:
            stats["skip"] += 1
        return

    last = None
    for attempt in range(3):
        try:
            r = sess.get(url, timeout=25)
            if r.status_code != 200:
                last = "HTTP %s" % r.status_code
                raise RuntimeError(last)
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            w, h = im.size
            if max(w, h) > MAX_EDGE:
                scale = MAX_EDGE / float(max(w, h))
                im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            im.save(out, "WEBP", quality=QUALITY, method=6)
            nbytes = os.path.getsize(out)
            rec = {"sid": sid, "url": url, "webp": shard + "/" + base,
                   "bytes": nbytes, "w": im.size[0], "h": im.size[1]}
            with lock:
                stats["ok"] += 1
                stats["bytes"] += nbytes
                with open(LOG, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return
        except Exception as e:  # noqa: BLE001
            last = str(e)[:80]
            time.sleep((1.5 ** attempt) + random.random())
    with lock:
        stats["err"] += 1
        errors.append((sid, last))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    urls = json.load(open(URLS, encoding="utf-8"))
    items = sorted(urls.items(), key=lambda kv: int(kv[0]))
    if args.limit:
        # spread the sample across the whole id range instead of the first N
        step = max(1, len(items) // args.limit)
        items = items[::step][: args.limit]

    total = len(items)
    print("covers to fetch: %d (workers=%d, max_edge=%d)" % (total, args.workers, MAX_EDGE), flush=True)
    t0 = time.time()
    done = 0

    def run(sess, chunk):
        nonlocal done
        for sid, imgs in chunk:
            fetch_one(sid, imgs, sess)
            with lock:
                done += 1
                if done % 500 == 0:
                    el = time.time() - t0
                    print("  %d/%d ok=%d err=%d skip=%d avg=%.1fKB %.1f/s" % (
                        done, total, stats["ok"], stats["err"], stats["skip"],
                        (stats["bytes"] / max(1, stats["ok"])) / 1024.0, done / el), flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for w in range(args.workers):
            ex.submit(run, requests.Session(), items[w::args.workers])

    el = time.time() - t0
    print("DONE ok=%d err=%d skip=%d in %.0fs (%.1f/s)" % (
        stats["ok"], stats["err"], stats["skip"], el, total / max(1e-6, el)), flush=True)
    if stats["ok"]:
        print("avg %.1f KB  total %.1f MB" % (
            stats["bytes"] / stats["ok"] / 1024.0, stats["bytes"] / 1048576.0), flush=True)
    if errors:
        print("error sample:", errors[:8], flush=True)


if __name__ == "__main__":
    main()
