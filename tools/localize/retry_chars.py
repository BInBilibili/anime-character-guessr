"""Retry pass: re-fetch characters that failed in fetch_chars.py (rate-limit resilience).

- reads existing chars_data.jsonl to know which ids succeeded
- skips images already on disk
- 3 attempts with exponential backoff + jitter
- appends to the jsonl (never truncates)
"""
import urllib.request, json, re, os, io, time, random, argparse
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
MAX_EDGE, QUALITY = 320, 82


def char_ids():
    s = open(ID_TAGS, encoding="utf-8").read()
    return sorted({int(k) for k in re.findall(r"(?<![\d.])(\d+)\s*:\s*\[", s)})


def basename_of(url):
    return url.split("?")[0].rsplit("/", 1)[-1].rsplit(".", 1)[0]


def shard_of(bn):
    h = bn[-5:-3] if len(bn) >= 7 else bn[:2]
    return re.sub(r"[^0-9a-zA-Z]", "_", h).ljust(2, "_")[:2]


def get(url, tries=3):
    last = None
    for a in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45).read()
        except Exception as e:
            last = e
            time.sleep((1.5 ** a) + random.random())
    raise last


def one(cid):
    try:
        d = json.loads(get("https://api.bgm.tv/v0/characters/%d" % cid))
        img = (d.get("images") or {}).get("medium")
        out = {"id": cid, "webp": None}
        if img:
            bn, sh = basename_of(img), None
            sh = shard_of(bn)
            dst_dir = os.path.join(OUT_IMG, sh)
            dst = os.path.join(dst_dir, bn + ".webp")
            out["webp"] = "chars/%s/%s.webp" % (sh, bn)
            out["src_url"] = img
            if not os.path.exists(dst):
                # small stagger so 12 workers don't hammer lain.bgm.tv in lockstep
                time.sleep(random.random() * 0.4)
                im = Image.open(io.BytesIO(get(img))).convert("RGB")
                im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
                os.makedirs(dst_dir, exist_ok=True)
                tmp = dst + ".tmp%d" % os.getpid()
                im.save(tmp, "WEBP", quality=QUALITY, method=6)
                os.replace(tmp, dst)
            out["bytes"] = os.path.getsize(dst)
        return out
    except Exception as e:
        return {"id": cid, "error": "%s: %s" % (type(e).__name__, e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--rounds", type=int, default=4)
    args = ap.parse_args()

    want = set(char_ids())
    for rnd in range(1, args.rounds + 1):
        have = set()
        if os.path.exists(OUT_DATA):
            with open(OUT_DATA, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        have.add(json.loads(line)["id"])
                    except Exception:
                        pass
        missing = sorted(want - have)
        print("round %d: have=%d missing=%d" % (rnd, len(have), len(missing)), flush=True)
        if not missing:
            print("ALL COMPLETE", flush=True)
            return

        ok = err = 0
        t0 = time.time()
        errs = []
        with open(OUT_DATA, "a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(one, cid): cid for cid in missing}
            for n, fut in enumerate(as_completed(futs), 1):
                r = fut.result()
                if "error" in r:
                    err += 1
                    if len(errs) < 5:
                        errs.append("%s -> %s" % (r["id"], r["error"]))
                else:
                    ok += 1
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                if n % 200 == 0 or n == len(missing):
                    el = time.time() - t0
                    print("  %5d/%d ok=%d err=%d %.0fs (%.1f/s)"
                          % (n, len(missing), ok, err, el, n / max(el, .001)), flush=True)
        for e in errs:
            print("   err sample:", e, flush=True)
        if ok == 0:
            print("no progress this round, stopping", flush=True)
            return


if __name__ == "__main__":
    main()
