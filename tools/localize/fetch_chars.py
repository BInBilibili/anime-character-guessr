"""Fetch Bangumi character data + images, convert to WebP, for full local hosting.

Usage:
  python fetch_chars.py --limit 300          # smoke test
  python fetch_chars.py                      # full run (32709)
  python fetch_chars.py --limit 300 --workers 24
"""
import urllib.request, json, re, os, io, sys, time, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ACG_REPO") or os.path.abspath(os.path.join(_HERE, "..", ".."))
WORK = os.environ.get("ACG_WORK") or os.path.join(_HERE, "_work")
os.makedirs(WORK, exist_ok=True)
ID_TAGS = os.path.join(REPO, "client", "src", "data", "id_tags.js")
OUT_IMG = os.path.join(REPO, "client", "public", "chars")
OUT_DATA = os.path.join(WORK, "chars_data.jsonl")
UA = {"User-Agent": "anime-character-guessr/1.0 (https://github.com/BInBilibili/anime-character-guessr)"}
MAX_EDGE = 320
QUALITY = 82


def log(*a):
    print(*a, flush=True)


def char_ids():
    s = open(ID_TAGS, encoding="utf-8").read()
    return sorted({int(k) for k in re.findall(r"(?<![\d.])(\d+)\s*:\s*\[", s)})


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45).read()


def basename_of(url):
    """https://lain.bgm.tv/r/400/pic/crt/l/7b/3a/1_crt_FEkJM.jpg -> 1_crt_FEkJM"""
    path = url.split("?")[0]
    return path.rsplit("/", 1)[-1].rsplit(".", 1)[0]


def shard_of(bn):
    """last-5-char hash, first 2 chars -> even spread across 256 dirs"""
    h = bn[-5:-3] if len(bn) >= 7 else bn[:2]
    return re.sub(r"[^0-9a-zA-Z]", "_", h).ljust(2, "_")[:2]


def one(cid):
    try:
        raw = get("https://api.bgm.tv/v0/characters/%d" % cid)
        d = json.loads(raw)
        img = (d.get("images") or {}).get("medium")
        out = {"id": cid, "raw": d, "webp": None}
        if img:
            bn = basename_of(img)
            sh = shard_of(bn)
            dst_dir = os.path.join(OUT_IMG, sh)
            dst = os.path.join(dst_dir, bn + ".webp")
            out["webp"] = "chars/%s/%s.webp" % (sh, bn)
            out["src_url"] = img
            if not os.path.exists(dst):
                blob = get(img)
                im = Image.open(io.BytesIO(blob)).convert("RGB")
                im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
                os.makedirs(dst_dir, exist_ok=True)
                tmp = dst + ".tmp%d" % os.getpid()
                im.save(tmp, "WEBP", quality=QUALITY, method=6)
                os.replace(tmp, dst)
                out["bytes"] = os.path.getsize(dst)
            else:
                out["bytes"] = os.path.getsize(dst)
        return out
    except Exception as e:
        return {"id": cid, "error": "%s: %s" % (type(e).__name__, e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    ids = char_ids()
    if args.offset:
        ids = ids[args.offset:]
    if args.limit:
        ids = ids[: args.limit]
    log("characters to fetch: %d | workers: %d" % (len(ids), args.workers))

    os.makedirs(OUT_IMG, exist_ok=True)
    t0 = time.time()
    ok = err = 0
    total_bytes = 0
    done = 0
    errors = []
    with open(OUT_DATA, "w", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(one, cid): cid for cid in ids}
        for fut in as_completed(futs):
            r = fut.result()
            done += 1
            if "error" in r:
                err += 1
                if len(errors) < 10:
                    errors.append("%s -> %s" % (r["id"], r["error"]))
            else:
                ok += 1
                total_bytes += r.get("bytes") or 0
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            if done % 100 == 0 or done == len(ids):
                el = time.time() - t0
                log("  %5d/%d  ok=%d err=%d  %.1f MB  %.0fs (%.1f/s)"
                    % (done, len(ids), ok, err, total_bytes / 1048576, el, done / max(el, 0.001)))

    log("")
    log("DONE ok=%d err=%d | images %.1f MB avg %.1f KB | %.0fs"
        % (ok, err, total_bytes / 1048576, (total_bytes / max(ok, 1)) / 1024, time.time() - t0))
    if errors:
        log("first errors:")
        for e in errors:
            log("  " + e)


if __name__ == "__main__":
    main()
